import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import alerts
from db import get_db
from models import Alert
from schemas import AlertOut, AlertRunResult

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
