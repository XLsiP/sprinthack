"""REAL: CMS NPPES NPI Registry (free, no API key).

Confirms a provider exists and is active, and lists their state license numbers.
It does not return expiration dates; those come from state boards.
"""
from typing import Optional

import httpx

from models import Associate, Credential
from verify.base import VerificationResult

NPI_URL = "https://npiregistry.cms.hhs.gov/api/"


def npi_checksum_ok(npi: str) -> bool:
    """Luhn check over the NPI with the 80840 health-industry prefix."""
    if len(npi) != 10 or not npi.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed("80840" + npi)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def lookup_npi(npi: str) -> Optional[dict]:
    """Return the NPI Registry record for `npi`, or None if not found."""
    resp = httpx.get(NPI_URL, params={"version": "2.1", "number": npi}, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    return results[0] if results else None


def _norm(value: Optional[str]) -> str:
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def match_license(provider: dict, number: Optional[str], state: Optional[str]) -> bool:
    """True if the registry record lists this license number (and state, if given)."""
    if not _norm(number):
        return False
    for tax in provider.get("taxonomies", []):
        if _norm(tax.get("license")) != _norm(number):
            continue
        if not state or _norm(tax.get("state")) == _norm(state):
            return True
    return False


class NppesVerifier:
    source = "NPPES"

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        npi = associate.npi or credential.number
        if not npi:
            return VerificationResult("not_found", self.source, {"reason": "No NPI on file"})
        if not npi_checksum_ok(npi):
            # Seed NPIs fail the checksum on purpose so they can never match a real provider.
            return VerificationResult("not_found", self.source, {"npi": npi, "reason": "Invalid NPI checksum"})
        try:
            provider = lookup_npi(npi)
        except httpx.HTTPError as exc:
            return VerificationResult("error", self.source, {"npi": npi, "reason": str(exc)})
        if provider is None:
            return VerificationResult("not_found", self.source, {"npi": npi, "reason": "NPI not in registry"})
        basic = provider.get("basic", {})
        details = {
            "npi": npi,
            "registry_name": " ".join(p for p in (basic.get("first_name"), basic.get("last_name")) if p)
            or basic.get("organization_name"),
            "registry_status": basic.get("status"),
            "enumeration_date": basic.get("enumeration_date"),
            "licenses": [
                {"license": t.get("license"), "state": t.get("state"), "taxonomy": t.get("desc")}
                for t in provider.get("taxonomies", [])
            ],
        }
        if basic.get("status") != "A":
            return VerificationResult("mismatch", self.source, {**details, "reason": "NPI is not active"})
        return VerificationResult("verified", self.source, details)
