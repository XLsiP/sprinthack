from dataclasses import dataclass, field
from typing import Literal, Protocol

from models import Associate, Credential


@dataclass
class VerificationResult:
    result: Literal["verified", "not_found", "excluded", "mismatch", "error"]
    source: str
    details: dict[str, object] = field(default_factory=dict)
    evidence_path: str | None = None


class Verifier(Protocol):
    source: str

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult: ...
