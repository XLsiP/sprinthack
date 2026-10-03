"""MOCK verification shared by the sources that have no real integration yet.

Outcomes are deterministic per credential number, so the seed data and repeated
"Verify now" clicks agree. Each subclass is a drop-in slot for a real adapter.
"""
import hashlib
import os
import time
from contextvars import ContextVar

from models import Associate, Credential
from verify.base import VerificationResult

MOCK_DELAY_SECONDS = float(os.environ.get("MOCK_DELAY_MS", "400")) / 1000
skip_delay: ContextVar[bool] = ContextVar("skip_delay", default=False)  # set during bulk runs


def pause() -> None:
    """Short delay so a mocked lookup feels like a real portal round trip."""
    if not skip_delay.get():
        time.sleep(MOCK_DELAY_SECONDS)


def mock_outcome(number: str) -> str:
    """About 1 in 40 credential numbers is "not found" at the source."""
    digest = hashlib.sha256(number.encode()).digest()
    return "not_found" if digest[0] % 40 == 0 else "verified"


class MockVerifier:
    source = "Mock"

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        pause()
        details: dict = {"mock": True, "searched_name": associate.name, "searched_number": credential.number}
        if not credential.number:
            return VerificationResult("not_found", self.source, {**details, "reason": "No number on file"})
        result = mock_outcome(credential.number)
        if result == "verified":
            details["source_status"] = "Active"
            details["source_expires"] = credential.expires_date.isoformat() if credential.expires_date else None
        else:
            details["reason"] = "No matching record at source"
        return VerificationResult(result, self.source, details)
