from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import Associate, Credential
from routers.deps import CREDENTIAL_LOAD, URGENCY, filter_associates
from schemas import CredentialOut, CredentialStatus

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.get("", response_model=list[CredentialOut])
def list_credentials(
    response: Response,
    status: Optional[list[CredentialStatus]] = Query(None),
    expires_before: Optional[date] = None,
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[CredentialOut]:
    """Credentials, most urgent first.

    `status` may be repeated. `expires_before` is exclusive and leaves out credentials that never expire.
    The `X-Total-Count` header is the number of matches before `limit` and `offset`.
    """
    query = filter_associates(select(Credential).join(Associate), manager, department, facility)
    if status:
        query = query.where(Credential.status.in_(status))
    if expires_before:
        query = query.where(Credential.expires_date < expires_before)
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(query.subquery())))

    query = query.options(*CREDENTIAL_LOAD).order_by(
        URGENCY, Credential.expires_date.is_(None), Credential.expires_date, Credential.id  # no expiry date sorts last
    )
    return [CredentialOut.from_model(c) for c in db.scalars(query.limit(limit).offset(offset))]
