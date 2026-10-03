from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Associate, Credential
from routers.deps import CREDENTIAL_LOAD, URGENCY, filter_associates
from schemas import CredentialOut, CredentialStatus

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.get("", response_model=list[CredentialOut])
def list_credentials(
    status: Optional[list[CredentialStatus]] = Query(None),
    expires_before: Optional[date] = None,
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[CredentialOut]:
    """Credentials, most urgent first. `status` may be repeated."""
    query = filter_associates(select(Credential).join(Associate), manager, department, facility)
    if status:
        query = query.where(Credential.status.in_(status))
    if expires_before:
        query = query.where(Credential.expires_date < expires_before)
    query = query.options(*CREDENTIAL_LOAD).order_by(URGENCY, Credential.expires_date, Credential.id)
    return [CredentialOut.from_model(c) for c in db.scalars(query.limit(limit).offset(offset))]
