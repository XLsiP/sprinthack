from datetime import datetime
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import alerts
from db import get_db
import mailer
from models import Alert, Credential, CredentialEmailContact
from routers.deps import CREDENTIAL_LOAD
from schemas import AlertOut, AlertRunResult, CredentialEmailContactOut
from status import days_left

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db)) -> list[AlertOut]:
    rows = db.scalars(select(Alert).order_by(Alert.sent_at.desc(), Alert.id.desc()))
    return [AlertOut.model_validate(alert) for alert in rows]


@router.post("/run", response_model=AlertRunResult)
def run_alert_sweep(db: Session = Depends(get_db)) -> AlertRunResult:
    hr_email = os.environ.get("HR_EMAIL", "").strip()
    if not hr_email:
        raise HTTPException(status_code=503, detail="HR_EMAIL must be configured to run alert sweeps")

    result = alerts.run_alerts(db, hr_email)
    db.commit()
    return AlertRunResult(**result)


@router.post("/credential/{credential_id}/email", response_model=CredentialEmailContactOut)
def email_credential_contact(credential_id: int, db: Session = Depends(get_db)) -> CredentialEmailContactOut:
    credential = db.scalar(
        select(Credential)
        .where(Credential.id == credential_id)
        .options(*CREDENTIAL_LOAD)
    )
    if credential is None:
        raise HTTPException(404, "Credential not found")
    remaining = days_left(credential.expires_date)
    if credential.status == "excluded" or remaining is None or remaining > 90:
        raise HTTPException(409, "Only expired or expiring credentials can be emailed")

    previous_contacts = credential.email_contacts
    kind = "follow_up" if previous_contacts else "initial"
    channel = mailer.deliver_credential_contact(credential, follow_up=kind == "follow_up")
    contact = CredentialEmailContact(
        credential_id=credential.id,
        kind=kind,
        sent_to=credential.associate.manager_email,
        sent_at=datetime.now(),
        channel=channel,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return CredentialEmailContactOut.model_validate(contact)
