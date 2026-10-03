from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db import get_db
from evidence import generate_evidence_pdf
from models import Credential, Verification

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{verification_id}.pdf", response_class=FileResponse)
def get_evidence_pdf(verification_id: int, db: Session = Depends(get_db)) -> FileResponse:
    verification = db.scalar(
        select(Verification)
        .where(Verification.id == verification_id)
        .options(
            selectinload(Verification.credential).selectinload(Credential.associate),
            selectinload(Verification.credential).selectinload(Credential.credential_type),
        )
    )
    if verification is None:
        raise HTTPException(404, "Verification not found")
    pdf_path = generate_evidence_pdf(verification)
    db.commit()
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="verification-%d.pdf" % verification.id,
    )
