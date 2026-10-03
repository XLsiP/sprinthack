from dataclasses import dataclass, field
from typing import Optional, Protocol

from models import Associate, Credential


@dataclass
class VerificationResult:
    result: str  # verified | not_found | excluded | mismatch | error
    source: str
    details: dict = field(default_factory=dict)
    evidence_path: Optional[str] = None


class Verifier(Protocol):
    source: str

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult: ...
