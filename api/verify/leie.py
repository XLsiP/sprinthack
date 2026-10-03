"""MOCK: OIG LEIE exclusion check. Replace with a lookup against the real LEIE CSV download.

Until then an associate is "excluded" only if the seed data recorded an exclusion for them.
"""
from models import Associate, Credential
from verify.base import VerificationResult
from verify.mock import pause


class LeieVerifier:
    source = "OIG LEIE"

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        pause()
        details = {"mock": True, "searched_name": associate.name}
        if any(v.result == "excluded" for v in credential.verifications):
            return VerificationResult("excluded", self.source, {**details, "exclusion_type": "1128(a)(1)"})
        return VerificationResult("verified", self.source, {**details, "source_status": "No exclusion found"})
