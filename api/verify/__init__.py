"""One adapter per issuing source. Look up by CredentialType.issuing_source."""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Credential, Verification
from status import refresh_credential
from verify.arrt import ArrtVerifier
from verify.base import VerificationResult
from verify.bls import BlsVerifier
from verify.indiana_license import IndianaLicenseVerifier
from verify.leie import LeieVerifier
from verify.michigan_lara import MichiganLaraVerifier
from verify.michigan_license import MichiganLicenseVerifier
from verify.mock import skip_delay
from verify.nmtcb import NmtcbVerifier
from verify.nppes import NppesVerifier

VERIFIERS = {
    v.source: v
    for v in (
        NppesVerifier(), LeieVerifier(), ArrtVerifier(), NmtcbVerifier(),
        IndianaLicenseVerifier(), MichiganLicenseVerifier(), BlsVerifier(),
    )
}


# Real integrations, used when the credential type's verify_method is "api". They take precedence over a
# mock registered for the same source, so synthetic data keeps its mocks and never calls a real site.
API_VERIFIERS = {v.source: v for v in (MichiganLaraVerifier(),)}


def verifier_for(credential: Credential):
    ctype = credential.credential_type
    if ctype.verify_method == "api" and ctype.issuing_source in API_VERIFIERS:
        return API_VERIFIERS[ctype.issuing_source]
    return VERIFIERS.get(ctype.issuing_source)


def apply_to_credential(credential: Credential, details: dict) -> None:
    """Copy what a real source reported (license number and dates) onto the credential."""
    if details.get("license_number"):
        credential.number = details["license_number"]
    for key, attribute in (("issued_date", "issued_date"), ("expires_date", "expires_date")):
        if details.get(key):
            setattr(credential, attribute, date.fromisoformat(details[key]))


def is_manual(credential: Credential) -> bool:
    """True for credentials a person verifies by hand at the source; no verifier may run on them."""
    return credential.credential_type.verify_method == "manual"


def record_manual(
    db: Session, credential: Credential, result: str, number: Optional[str] = None,
    expires_date: Optional[date] = None, issued_date: Optional[date] = None, note: Optional[str] = None,
) -> Verification:
    """Record a lookup a person did at the source, and update the credential from what they saw."""
    details: dict = {"entered_by_hand": True}
    if result == "verified":
        if number:
            credential.number = number.strip()
        if expires_date:
            credential.expires_date = expires_date
        if issued_date:
            credential.issued_date = issued_date
        details.update({
            "number": credential.number,
            "expires_date": credential.expires_date.isoformat() if credential.expires_date else None,
        })
    else:
        details["reason"] = "Not found at the source when checked by hand"
    if note:
        details["note"] = note.strip()
    verification = Verification(
        credential=credential,
        checked_at=datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
        source=credential.credential_type.issuing_source,
        result=result,
        details=details,
    )
    db.add(verification)
    refresh_credential(credential)
    return verification


def run(db: Session, credential: Credential, delay: bool = True) -> Verification:
    """Verify one credential against its source, record the result, and refresh its status."""
    source = credential.credential_type.issuing_source
    verifier = verifier_for(credential)
    if verifier is None:
        outcome = VerificationResult("error", source, {"reason": "No verifier for this source"})
    else:
        token = skip_delay.set(not delay)
        try:
            outcome = verifier.verify(credential.associate, credential)
        finally:
            skip_delay.reset(token)
    verification = Verification(
        credential=credential,
        checked_at=datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
        source=outcome.source,
        result=outcome.result,
        details=outcome.details,
        evidence_path=outcome.evidence_path,
    )
    if getattr(verifier, "updates_credential", False) and outcome.result in ("verified", "mismatch"):
        apply_to_credential(credential, outcome.details)
    db.add(verification)
    refresh_credential(credential)
    return verification
