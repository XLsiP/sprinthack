"""Verify credentials against public sources.

Wired up so far: the CMS NPI Registry (free, no API key).
It confirms a provider exists, is active, and lists their state license numbers.
It does NOT return expiration dates; those come from state boards.

Ideas for more sources:
  - OIG exclusion list (LEIE): https://oig.hhs.gov/exclusions/exclusions_list.asp
  - State licensing boards / Nursys for nurses
"""
import httpx

NPI_URL = "https://npiregistry.cms.hhs.gov/api/"


def lookup_npi(npi):
    """Return the NPI Registry record for `npi`, or None if not found."""
    resp = httpx.get(NPI_URL, params={"version": "2.1", "number": npi}, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    return results[0] if results else None


def _norm(value):
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def match_license(provider, number, state):
    """True if the registry record lists this license number (and state, if given)."""
    if not _norm(number):
        return False
    for tax in provider.get("taxonomies", []):
        if _norm(tax.get("license")) != _norm(number):
            continue
        if not state or _norm(tax.get("state")) == _norm(state):
            return True
    return False


def check_credential(provider, cred):
    """Return a verification status for one credential given the provider's NPI record."""
    if provider is None:
        return "npi_not_found"
    if provider.get("basic", {}).get("status") != "A":
        return "npi_inactive"
    if "license" not in cred["type"].lower():
        return "unverified"  # no public source wired up for this credential type yet
    return "verified" if match_license(provider, cred["number"], cred["state"]) else "mismatch"
