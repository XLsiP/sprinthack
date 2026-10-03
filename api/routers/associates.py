from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db import get_db
from models import Associate, Credential
from routers.deps import CREDENTIAL_LOAD, filter_associates
from schemas import AssociateDetail, AssociateOut, CredentialStatus

router = APIRouter(prefix="/associates", tags=["associates"])


@router.get("", response_model=list[AssociateOut])
def list_associates(
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    status: Optional[CredentialStatus] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[AssociateOut]:
    """Associates, optionally only those with at least one credential in `status`."""
    query = filter_associates(select(Associate), manager, department, facility)
    if status:
        query = query.where(Associate.credentials.any(Credential.status == status))
    query = query.options(selectinload(Associate.credentials)).order_by(Associate.name)
    return [AssociateOut.from_model(a) for a in db.scalars(query.limit(limit).offset(offset))]


@router.get("/{associate_id}", response_model=AssociateDetail)
def get_associate(associate_id: int, db: Session = Depends(get_db)) -> AssociateDetail:
    associate = db.scalar(
        select(Associate)
        .where(Associate.id == associate_id)
        .options(selectinload(Associate.credentials).options(*CREDENTIAL_LOAD))
    )
    if associate is None:
        raise HTTPException(404, "Associate not found")
    return AssociateDetail.from_model(associate)
