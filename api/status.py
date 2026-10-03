"""Derived credential status from the expiration date and the latest verification result."""
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Credential

# Most urgent first; list endpoints and "worst status" use this order.
SEVERITY = [
    "excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90", "unverified", "valid",
]
FAILED_RESULTS = {"not_found", "mismatch"}


def days_left(expires_date: Optional[date], today: Optional[date] = None) -> Optional[int]:
    if expires_date is None:
        return None
    return (expires_date - (today or date.today())).days


def compute_status(
    expires_date: Optional[date], last_result: Optional[str], today: Optional[date] = None,
    expiry_expected: bool = False,
) -> str:
    """Status from the expiration date and the latest conclusive verification result.

    Precedence: excluded, then expired, then verification_failed, then the expiry buckets.
    `expiry_expected` marks a credential type that expires: with no expiry date on file and nothing
    verified yet, such a credential is "unverified" rather than assumed valid.
    """
    if last_result == "excluded":
        return "excluded"
    left = days_left(expires_date, today)
    if left is not None and left < 0:
        return "expired"
    if last_result in FAILED_RESULTS:
        return "verification_failed"
    if left is None and expiry_expected and last_result is None:
        return "unverified"
    if left is None or left > 90:
        return "valid"
    if left <= 30:
        return "expiring_30"
    if left <= 60:
        return "expiring_60"
    return "expiring_90"


def worst(statuses: list[str]) -> Optional[str]:
    return min(statuses, key=SEVERITY.index) if statuses else None


def refresh_credential(credential: Credential, today: Optional[date] = None) -> None:
    # An "error" means the source could not be reached, so it must not clear an earlier exclusion or failure.
    conclusive = [v.result for v in credential.verifications if v.result != "error"]
    ctype = credential.credential_type
    credential.status = compute_status(
        credential.expires_date, conclusive[-1] if conclusive else None, today,
        expiry_expected=bool(ctype is not None and ctype.renewal_months),
    )


def refresh_statuses(db: Session, today: Optional[date] = None) -> None:
    """Recompute every stored status. Run at startup and by the daily job, since statuses age with the calendar."""
    loading = (selectinload(Credential.verifications), selectinload(Credential.credential_type))
    for credential in db.scalars(select(Credential).options(*loading)):
        refresh_credential(credential, today)
    db.commit()
