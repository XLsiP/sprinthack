"""REAL: ARDMS status lookup (the public Inteleos status verification directory).

Searches by name and reads each credential the directory lists for the person: its specialty, the
dates it is valid from and until, and its status. No login or CAPTCHA is involved; the directory
answers a plain page request.

It runs only when someone asks for it with "Verify all" (see ON_REQUEST_VERIFIERS in verify/__init__.py).
A name can match several people. They are never guessed between: the result is "error" marked
needs_review, for a person to check by hand. The same goes for a name with no match, since the
person may be listed under another name.
"""
import html
import re
import threading
import time
from datetime import datetime
from typing import Optional

import httpx

from models import Associate, Credential
from verify.base import VerificationResult

URL = "https://myportal.inteleos.org/status-verification-directory.html"
USER_AGENT = "Mozilla/5.0 (compatible; BeaconCredentialingTracker/1.0; employer credential verification)"
MIN_INTERVAL_SECONDS = 1.0  # at most one search a second, however many are queued

_lock = threading.Lock()
_last_request = 0.0


def fetch(name: str) -> str:
    """Run one search and return the page. Paced so searches never run back to back."""
    global _last_request
    with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            response = httpx.get(
                URL, params={"q": name}, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30,
            )
            response.raise_for_status()
            return response.text
        finally:
            _last_request = time.monotonic()


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _iso(value: str) -> Optional[str]:
    """`December 31 2026` -> `2026-12-31`."""
    try:
        return datetime.strptime(value.replace(",", "").strip(), "%B %d %Y").date().isoformat()
    except ValueError:
        return None


def parse(page: str) -> list[dict]:
    """One record per person on the results page. Raises ValueError if the page is not a results page."""
    start = page.find('id="status-verif-listing"')
    if start < 0:
        raise ValueError("The ARDMS directory returned a page that could not be read")
    listing = page[start:]
    people = []
    for panel in listing.split('class="panel-item"')[1:]:
        heading = re.search(r"<h6[^>]*>(.*?)</h6>", panel, re.S)
        if not heading:
            continue
        country = re.search(r"<span[^>]*>(.*?)</span>", heading.group(1), re.S)
        table = re.search(r"<tbody>(.*?)</tbody>", panel, re.S)
        heads = [_text(th).rstrip(":").lower() for th in re.findall(r"<th[^>]*>(.*?)</th>", panel, re.S)]
        credentials = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(1) if table else "", re.S):
            cells = dict(zip(heads, (_text(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S))))
            credentials.append({
                "credential": cells.get("credential", ""), "specialty": cells.get("specialty", ""),
                "valid_from": cells.get("valid from", ""), "valid_until": cells.get("valid until", ""),
                "status": cells.get("status", ""),
            })
        people.append({
            "name": _text(re.sub(r"<span.*?</span>", " ", heading.group(1), flags=re.S)),
            "country": _text(country.group(1)) if country else "",
            "credentials": credentials,
        })
    if not people and "No results found" not in listing[:2000]:
        raise ValueError("The ARDMS directory returned a page that could not be read")
    return people


def _letters(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


class ArdmsVerifier:
    source = "ARDMS"
    updates_credential = True  # verify.run copies the dates onto the credential

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        searched = {"searched_name": associate.name}
        try:
            people = parse(fetch(associate.name))
        except (httpx.HTTPError, ValueError) as exc:
            return VerificationResult("error", self.source, {**searched, "reason": "Could not check: %s" % exc})

        def review(reason: str) -> VerificationResult:
            return VerificationResult("error", self.source, {**searched, "needs_review": True, "reason": reason})

        if not people:
            return review("Nobody is listed under this name; they may be listed under another name. Check by hand.")
        if len(people) > 1:
            return review("%d people match this name; check by hand to pick the right one" % len(people))
        person = people[0]
        if _letters(associate.name.split()[-1]) not in _letters(person["name"]) or not person["credentials"]:
            return review("The directory's result did not clearly match this person. Check by hand.")

        rows = person["credentials"]
        active = [r for r in rows if r["status"].lower() == "active"]
        held = {}
        for r in rows:
            held.setdefault(r["credential"], []).append(r["specialty"])
        details: dict = {
            **searched,
            "name": person["name"],
            "credentials_held": "; ".join(
                "%s (%s)" % (name, ", ".join(s for s in specialties if s)) if any(specialties) else name
                for name, specialties in held.items()
            ),
            "source_status": ", ".join(dict.fromkeys(r["status"] for r in rows if r["status"])),
            "issued_date": min(filter(None, (_iso(r["valid_from"]) for r in rows)), default=None),
            # With several credentials, the one that runs out first is the date to track.
            "expires_date": min(filter(None, (_iso(r["valid_until"]) for r in active or rows)), default=None),
            "Country": person["country"],
            "lookup_url": URL,
        }
        for i, r in enumerate(rows, 1):
            label = "%d. %s" % (i, ", ".join(part for part in (r["credential"], r["specialty"]) if part))
            details[label] = ", ".join(part for part in (
                r["valid_from"] and "valid from %s" % r["valid_from"],
                r["valid_until"] and "until %s" % r["valid_until"], r["status"],
            ) if part)
        if not active:
            return VerificationResult("mismatch", self.source, {
                **details, "reason": "Status is %s" % (details["source_status"] or "unknown"),
            })
        if not details["expires_date"]:
            return review("The directory showed an active credential but no date that could be read. Check by hand.")
        return VerificationResult("verified", self.source, details)
