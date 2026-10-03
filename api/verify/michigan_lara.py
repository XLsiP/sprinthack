"""REAL: Michigan LARA license lookup (the public MiPLUS / Accela search page).

Searches by license number when the credential already has one, otherwise by first and last name,
and reads the license type, number, status and dates from the state's record. No login or CAPTCHA
is involved; the page's own anti-forgery token is fetched and sent back as a browser would.

A name can match several records. Records that are plainly the same person (same first, middle and
last name) are treated as one, taking the license that expires last. Different people with the same
name are never guessed between: the result is "error" with the candidates listed for a person to pick.
"""
import html
import re
import threading
import time
from datetime import date, datetime
from typing import Optional

import httpx

from models import Associate, Credential
from verify.base import VerificationResult

URL = "https://aca-prod.accela.com/MILARA/GeneralProperty/PropertyLookUp.aspx?isLicensee=Y&TabName=APO"
ORIGIN = "https://aca-prod.accela.com"
FORM = "ctl00$PlaceHolderMain$refLicenseeSearchForm$"
SEARCH_BUTTON = "ctl00$PlaceHolderMain$btnNewSearch"
FIELDS = ("ddlLicenseType", "txtLicenseNumber", "txtBusiLicense", "txtFirstName", "txtMiddleInitial",
          "txtLastName", "txtBusiName", "txtTitle", "txtInsuranceCompany")
USER_AGENT = "Mozilla/5.0 (compatible; BeaconCredentialingTracker/1.0; employer license verification)"
MIN_INTERVAL_SECONDS = 1.0  # at most one search a second, however many are queued

_lock = threading.Lock()
_last_request = 0.0


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _iso(value: str) -> Optional[str]:
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def hidden_fields(page: str) -> dict[str, str]:
    fields = {}
    for tag in re.findall(r'<input[^>]*type="hidden"[^>]*>', page):
        name = re.search(r'name="([^"]*)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[name.group(1)] = html.unescape(value.group(1)) if value else ""
    return fields


def no_results(page: str) -> bool:
    return "Your search returned no results" in page


def parse_detail(page: str) -> Optional[dict]:
    """The single-record page the site shows when exactly one license matches."""
    body = _text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S))
    number = re.search(r"License Number: (\S+)", body)
    if not number:
        return None
    def field(label: str, stop: str) -> str:
        match = re.search(r"%s: (.*?) %s" % (label, stop), body)
        return match.group(1).strip() if match else ""
    license_type = re.search(r"records associated with (.*?), License Number", body)
    return {
        "license_type": license_type.group(1).strip() if license_type else "",
        "license_number": number.group(1),
        "name": field("Name", "License Issue Date"),
        "status": field("License Status", "County"),
        "issued_date": _iso(field("License Issue Date", "License Expiration Date")),
        "expires_date": _iso(field("License Expiration Date", "License Status")),
        "county": field("County", "Related Records"),
    }


def parse_list(page: str) -> list[dict]:
    """The results table shown when several licenses match."""
    records = []
    for row in re.findall(r'<tr[^>]*class="[^"]*ACA_TabRow_(?:Odd|Even)[^"]*"[^>]*>(.*?)</tr>', page, re.S):
        cells = [_text(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 9:
            continue
        records.append({
            "license_type": cells[0], "license_number": cells[1],
            "name": " ".join(part for part in (cells[2], cells[3], cells[4]) if part),
            "status": cells[7], "issued_date": None, "expires_date": _iso(cells[8]), "county": "",
        })
    return records


def fetch(first: str = "", last: str = "", number: str = "") -> tuple[str, str]:
    """Run one search and return (final URL, page). Paced so searches never run back to back."""
    global _last_request
    with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30) as client:
                form = hidden_fields(client.get(URL).text)
                form.update({FORM + name: "" for name in FIELDS})
                form.update({
                    "__EVENTTARGET": SEARCH_BUTTON, "__EVENTARGUMENT": "",
                    FORM + "txtFirstName": first, FORM + "txtLastName": last, FORM + "txtLicenseNumber": number,
                })
                response = client.post(URL, data=form, headers={"Referer": URL, "Origin": ORIGIN})
                response.raise_for_status()
                return str(response.url), response.text
        finally:
            _last_request = time.monotonic()


def lookup(first: str = "", last: str = "", number: str = "") -> list[dict]:
    """Every license record matching the search. Raises httpx.HTTPError or ValueError on failure."""
    url, page = fetch(first, last, number)
    if "Error.aspx" in url:
        raise ValueError("The Michigan lookup page rejected the search")
    if "LicenseeDetail.aspx" in url:
        record = parse_detail(page)
        if record is None:
            raise ValueError("The Michigan lookup returned a record that could not be read")
        return [record]
    if no_results(page):
        return []
    records = parse_list(page)
    if not records:
        raise ValueError("The Michigan lookup returned a page that could not be read")
    return records


def split_name(name: str) -> tuple[str, str]:
    """First and last name for the search: the last word is the surname, the rest the first name."""
    parts = name.split()
    return (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else ("", name)


def _same_person(records: list[dict]) -> bool:
    return len({re.sub(r"[^a-z]", "", r["name"].lower()) for r in records}) == 1


def _expiry(record: dict) -> date:
    return date.fromisoformat(record["expires_date"]) if record["expires_date"] else date.min


class MichiganLaraVerifier:
    source = "Michigan LARA"
    updates_credential = True  # verify.run copies the license number and dates onto the credential

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        first, last = split_name(associate.name)
        searched = {"searched_number": credential.number} if credential.number else {"searched_name": associate.name}
        try:
            records = lookup(number=credential.number) if credential.number else lookup(first=first, last=last)
        except (httpx.HTTPError, ValueError) as exc:
            return VerificationResult("error", self.source, {**searched, "reason": "Could not check: %s" % exc})

        if not records:
            return VerificationResult("not_found", self.source, {
                **searched, "reason": "No Michigan license found under this %s"
                % ("number" if credential.number else "name"),
            })
        if not _same_person(records):
            return VerificationResult("error", self.source, {
                **searched, "needs_review": True,
                "reason": "%d different people match this name; enter the license number to pick one" % len(records),
                "candidates": records,
            })

        record = max(records, key=lambda r: (r["status"] == "Active", _expiry(r)))
        details = {**searched, **record, "lookup_url": URL}
        if len(records) > 1:
            details["other_licenses"] = [r for r in records if r is not record]
        if record["status"] != "Active":
            return VerificationResult("mismatch", self.source, {
                **details, "reason": "License status is %s" % (record["status"] or "unknown"),
            })
        return VerificationResult("verified", self.source, details)
