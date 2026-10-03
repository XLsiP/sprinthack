"""One adapter per issuing source. Look up by CredentialType.issuing_source."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Credential, Verification
from status import refresh_credential
from verify.arrt import ArrtVerifier
from verify.base import VerificationResult
from verify.bls import BlsVerifier
from verify.indiana_license import IndianaLicenseVerifier
from verify.leie import LeieVerifier
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


def is_manual(credential: Credential) -> bool:
    """True for credentials a person verifies by hand at the source; no verifier may run on them."""
    return credential.credential_type.verify_method == "manual"


def run(db: Session, credential: Credential, delay: bool = True) -> Verification:
    """Verify one credential against its source, record the result, and refresh its status."""
    source = credential.credential_type.issuing_source
    verifier = VERIFIERS.get(source)
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
    db.add(verification)
    refresh_credential(credential)
    return verification
