"""Derived credential status from the expiration date and the latest verification result."""
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Credential

# Most urgent first; list endpoints and "worst status" use this order.
SEVERITY = ["excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90", "valid"]
FAILED_RESULTS = {"not_found", "mismatch"}


def days_left(expires_date: Optional[date], today: Optional[date] = None) -> Optional[int]:
    if expires_date is None:
        return None
    return (expires_date - (today or date.today())).days


def derive_status(expires_date: Optional[date], last_result: Optional[str], today: Optional[date] = None) -> str:
    if last_result == "excluded":
        return "excluded"
    left = days_left(expires_date, today)
    if left is not None and left < 0:
        return "expired"
    if last_result in FAILED_RESULTS:
        return "verification_failed"
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
    last = credential.verifications[-1].result if credential.verifications else None
    credential.status = derive_status(credential.expires_date, last, today)


def refresh_statuses(db: Session, today: Optional[date] = None) -> None:
    """Recompute every stored status. Run at startup and by the daily job, since statuses age with the calendar."""
    for credential in db.scalars(select(Credential).options(selectinload(Credential.verifications))):
        refresh_credential(credential, today)
    db.commit()
