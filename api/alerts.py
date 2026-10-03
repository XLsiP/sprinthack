"""Threshold selection and outbox creation for credential alerts."""
from collections import Counter
from datetime import date, datetime
from typing import Optional, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Alert, Credential
from status import days_left, refresh_credential


class AlertRunSummary(TypedDict):
    sent: int
    by_threshold: dict[str, int]


def threshold_for_credential(credential: Credential, today: Optional[date] = None) -> Optional[str]:
    refresh_credential(credential, today)
    if credential.status == "excluded":
        return "excluded"

    remaining = days_left(credential.expires_date, today)
    if remaining is None:
        return None
    if remaining <= 0:
        return "expired"
    if remaining <= 30:
        return "30"
    if remaining <= 60:
        return "60"
    if remaining <= 90:
        return "90"
    return None


def run_alerts(db: Session, hr_email: str, today: Optional[date] = None) -> AlertRunSummary:
    credentials = db.scalars(
        select(Credential).options(
            selectinload(Credential.associate),
            selectinload(Credential.verifications),
        )
    ).all()
    existing = {
        (credential_id, threshold)
        for credential_id, threshold in db.execute(select(Alert.credential_id, Alert.threshold))
    }

    by_threshold: Counter[str] = Counter()
    sent_at = datetime.now()
    for credential in credentials:
        threshold = threshold_for_credential(credential, today)
        if threshold is None or (credential.id, threshold) in existing:
            continue

        recipients = dict.fromkeys((credential.associate.manager_email, hr_email))
        for recipient in recipients:
            db.add(
                Alert(
                    credential_id=credential.id,
                    threshold=threshold,
                    sent_to=recipient,
                    sent_at=sent_at,
                    channel="outbox",
                )
            )
            by_threshold[threshold] += 1
        existing.add((credential.id, threshold))

    db.flush()
    return {"sent": sum(by_threshold.values()), "by_threshold": dict(by_threshold)}
