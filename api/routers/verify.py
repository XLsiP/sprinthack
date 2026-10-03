from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import verify
from db import get_db
from models import Associate, Credential
from routers.deps import CREDENTIAL_LOAD, filter_associates
from schemas import VerificationOut, VerifyAllOut

router = APIRouter(prefix="/verify", tags=["verify"])


@router.post("/credential/{credential_id}", response_model=VerificationOut)
def verify_credential(credential_id: int, db: Session = Depends(get_db)) -> VerificationOut:
    credential = db.scalar(select(Credential).where(Credential.id == credential_id).options(*CREDENTIAL_LOAD))
    if credential is None:
        raise HTTPException(404, "Credential not found")
    verification = verify.run(db, credential)
    db.commit()
    return VerificationOut.model_validate(verification)


@router.post("/associate/{associate_id}", response_model=list[VerificationOut])
def verify_associate(associate_id: int, db: Session = Depends(get_db)) -> list[VerificationOut]:
    credentials = db.scalars(
        select(Credential).where(Credential.associate_id == associate_id).options(*CREDENTIAL_LOAD)
    ).all()
    if not credentials:
        raise HTTPException(404, "Associate not found or has no credentials")
    # One short pause for the whole associate rather than one per credential.
    verifications = [verify.run(db, c, delay=(i == 0)) for i, c in enumerate(credentials)]
    db.commit()
    return [VerificationOut.model_validate(v) for v in verifications]


@router.post("/all", response_model=VerifyAllOut)
def verify_all(
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    db: Session = Depends(get_db),
) -> VerifyAllOut:
    """Re-verify every credential in scope (all of them when no filter is given)."""
    query = filter_associates(select(Credential).join(Associate), manager, department, facility)
    results: Counter[str] = Counter()
    for credential in db.scalars(query.options(*CREDENTIAL_LOAD)):
        results[verify.run(db, credential, delay=False).result] += 1
    db.commit()
    return VerifyAllOut(checked=sum(results.values()), by_result=dict(results))
