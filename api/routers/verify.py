from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import verify
from db import get_db
from models import Associate, Credential
from routers.deps import CREDENTIAL_LOAD, filter_associates
from schemas import ManualVerificationIn, VerificationOut, VerifyAllOut

router = APIRouter(prefix="/verify", tags=["verify"])


@router.post("/credential/{credential_id}", response_model=VerificationOut)
def verify_credential(credential_id: int, db: Session = Depends(get_db)) -> VerificationOut:
    credential = db.scalar(select(Credential).where(Credential.id == credential_id).options(*CREDENTIAL_LOAD))
    if credential is None:
        raise HTTPException(404, "Credential not found")
    if verify.is_manual(credential):
        raise HTTPException(
            409, "This credential is verified by hand at %s; record the result instead"
            % credential.credential_type.issuing_source,
        )
    verification = verify.run(db, credential)
    db.commit()
    return VerificationOut.model_validate(verification)


@router.post("/credential/{credential_id}/manual", response_model=VerificationOut)
def record_manual_verification(
    credential_id: int, body: ManualVerificationIn, db: Session = Depends(get_db)
) -> VerificationOut:
    """Record the result of a lookup a person did at the source (sources the app cannot check itself)."""
    credential = db.scalar(select(Credential).where(Credential.id == credential_id).options(*CREDENTIAL_LOAD))
    if credential is None:
        raise HTTPException(404, "Credential not found")
    ctype = credential.credential_type
    if ctype.verify_method == "mock":
        raise HTTPException(409, "This credential is checked automatically; results cannot be entered by hand")
    if body.result == "verified" and ctype.renewal_months and not (body.expires_date or credential.expires_date):
        raise HTTPException(422, "expires_date: an expiry date is required for a credential that expires")
    if body.expires_date and body.issued_date and body.issued_date > body.expires_date:
        raise HTTPException(422, "issued_date: must not be after expires_date")
    verification = verify.record_manual(
        db, credential, body.result, number=body.number, expires_date=body.expires_date,
        issued_date=body.issued_date, note=body.note, credentials_held=body.credentials_held,
        source_status=body.source_status, source_details=body.source_details,
    )
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
    automatic = [c for c in credentials if not verify.is_manual(c)]  # hand-verified credentials are left alone
    verifications = [verify.run(db, c, delay=(i == 0)) for i, c in enumerate(automatic)]
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
    skipped = 0
    for credential in db.scalars(query.options(*CREDENTIAL_LOAD)):
        if verify.is_manual(credential):
            skipped += 1
            continue
        results[verify.run(db, credential, delay=False).result] += 1
    db.commit()
    return VerifyAllOut(checked=sum(results.values()), by_result=dict(results), skipped_manual=skipped)
