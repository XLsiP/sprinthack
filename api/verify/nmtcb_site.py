"""REAL: NMTCB certificant verification (the public search on nmtcb.org).

Searches by last and first name, and when exactly one person matches, reads their page: the
certifications held, the current status and the date each is certified through. No login or
CAPTCHA is involved. (verify/nmtcb.py is the MOCK used by the synthetic data.)

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
from verify.michigan_lara import split_name

ORIGIN = "https://www.nmtcb.org"
SEARCH = ORIGIN + "/verification/results"
USER_AGENT = "Mozilla/5.0 (compatible; BeaconCredentialingTracker/1.0; employer credential verification)"
MIN_INTERVAL_SECONDS = 1.0  # at most one request a second, however many are queued

_lock = threading.Lock()
_last_request = 0.0


def fetch(url: str, params: Optional[dict] = None) -> str:
    """Fetch one page. Paced so requests never run back to back."""
    global _last_request
    with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            response = httpx.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30,
            )
            response.raise_for_status()
            return response.text
        finally:
            _last_request = time.monotonic()


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _main(page: str) -> str:
    section = re.search(r'id="main-section".*?</section>', page, re.S)
    if not section:
        raise ValueError("The NMTCB site returned a page that could not be read")
    return section.group(0)


def parse_results(page: str) -> list[dict]:
    """The people a name search matched: their page and how the list names them."""
    section = _main(page)
    people = [
        {"path": path, "name": _text(name)}
        for path, name in re.findall(r'<a href="(/verification/\d+)"[^>]*>(.*?)</a>', section, re.S)
    ]
    if not people and "cannot find an entry" not in section:
        raise ValueError("The NMTCB site returned a page that could not be read")
    return people


def parse_person(page: str) -> dict:
    """One person's page: each titled block, plus the dates inside "Certified Through"."""
    blocks = {}
    for block in re.split(r'<div[^>]*class="details-block"[^>]*>', _main(page))[1:]:
        title = re.search(r"<h6[^>]*>(.*?)</h6>", block, re.S)
        if title:
            blocks[_text(title.group(1)).lower()] = block[title.end():]
    if "current status" not in blocks:
        raise ValueError("The NMTCB site returned a record that could not be read")
    statuses = [_text(dd) for dd in re.findall(r"<dd[^>]*>(.*?)</dd>", blocks["current status"], re.S)]
    as_of = re.search(r"information as of:\s*(\d{1,2}/\d{1,2}/\d{4})", _text(page))
    return {
        "name": _text(blocks.get("name", "")),
        "location": _text(blocks.get("address", "")),
        "certifications": _text(blocks.get("certifications held", "")),
        "status": _text(blocks["current status"]),
        "statuses": statuses,
        "certified_through": _text(blocks.get("certified through", "")),
        "dates": re.findall(r'<time datetime="(\d{4}-\d{2}-\d{2})"', blocks.get("certified through", "")),
        "as_of": as_of.group(1) if as_of else "",
    }


def _letters(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


class NmtcbSiteVerifier:
    source = "NMTCB"
    updates_credential = True  # verify.run copies the date onto the credential

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        first, last = split_name(associate.name)
        searched = {"searched_name": associate.name}

        def review(reason: str) -> VerificationResult:
            return VerificationResult("error", self.source, {**searched, "needs_review": True, "reason": reason})

        try:
            people = parse_results(fetch(SEARCH, {"LastName": last, "FirstName": first}))
            if not people:
                return review("Nobody is listed under this name; they may be listed under another name. Check by hand.")
            if len(people) > 1:
                return review("%d people match this name; check by hand to pick the right one" % len(people))
            lookup_url = ORIGIN + people[0]["path"]
            person = parse_person(fetch(lookup_url))
        except (httpx.HTTPError, ValueError) as exc:
            return VerificationResult("error", self.source, {**searched, "reason": "Could not check: %s" % exc})

        if _letters(last) not in _letters(person["name"]):
            return review("The site's result did not clearly match this person. Check by hand.")
        details = {
            **searched,
            "name": person["name"],
            "credentials_held": person["certifications"],
            "source_status": person["status"],
            "expires_date": min(person["dates"], default=None),
            "Location": person["location"],
            "Certified through": person["certified_through"],
            "Accurate as of": person["as_of"],
            "lookup_url": lookup_url,
        }
        if not person["statuses"] or any(status.upper() != "ACTIVE" for status in person["statuses"]):
            return VerificationResult("mismatch", self.source, {
                **details, "reason": "Status is %s" % (person["status"] or "unknown"),
            })
        if not details["expires_date"]:
            return review("The site showed an active certification but no date that could be read. Check by hand.")
        return VerificationResult("verified", self.source, details)
