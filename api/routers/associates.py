from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from db import get_db
from models import Associate, Credential
from routers.deps import CREDENTIAL_LOAD, URGENCY, filter_associates
from schemas import AssociateDetail, AssociateOut, CredentialStatus
from status import SEVERITY

router = APIRouter(prefix="/associates", tags=["associates"])

# Rank of an associate's most urgent credential; associates with no credentials sort last.
WORST_URGENCY = func.coalesce(
    select(func.min(URGENCY)).where(Credential.associate_id == Associate.id).correlate(Associate).scalar_subquery(),
    len(SEVERITY),
)


@router.get("", response_model=list[AssociateOut])
def list_associates(
    response: Response,
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    status: Optional[list[CredentialStatus]] = Query(None),
    sort: Literal["urgency", "name"] = "urgency",
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[AssociateOut]:
    """Associates, most urgent first by default.

    `status` may be repeated and keeps associates with at least one credential in any of those statuses.
    The `X-Total-Count` header is the number of matches before `limit` and `offset`.
    """
    query = filter_associates(select(Associate), manager, department, facility)
    if status:
        query = query.where(Associate.credentials.any(Credential.status.in_(status)))
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(query.subquery())))

    order = (WORST_URGENCY, Associate.name, Associate.id) if sort == "urgency" else (Associate.name, Associate.id)
    query = query.options(selectinload(Associate.credentials)).order_by(*order)
    return [AssociateOut.from_model(a) for a in db.scalars(query.limit(limit).offset(offset))]


@router.get("/{associate_id}", response_model=AssociateDetail)
def get_associate(associate_id: int, db: Session = Depends(get_db)) -> AssociateDetail:
    """One associate with their credentials (most urgent first) and each credential's latest verification."""
    associate = db.scalar(
        select(Associate)
        .where(Associate.id == associate_id)
        .options(selectinload(Associate.credentials).options(*CREDENTIAL_LOAD))
    )
    if associate is None:
        raise HTTPException(404, "Associate not found")
    return AssociateDetail.from_model(associate)
