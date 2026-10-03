from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, CredentialType, Verification
import evidence


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "EVIDENCE_DIR", tmp_path / "evidence")

    def render_pdf(document, output_path):
        output_path.write_bytes(b"%PDF-1.4\nsynthetic test PDF\n%%EOF")

    monkeypatch.setattr(evidence, "_render_pdf", render_pdf)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


def add_verification(name="Jordan Reyes", details=None):
    with SessionLocal() as db:
        credential_type = CredentialType(
            name="ARRT RT(R)", issuing_source="ARRT", verify_method="mock", renewal_months=12
        )
        associate = Associate(
            name=name,
            role="Radiologic Technologist",
            department="Radiology",
            facility="Epworth Hospital",
            state="IN",
            manager_email="rad@example.org",
        )
        credential = Credential(
            credential_type=credential_type,
            number="RT-12345",
            issued_date=date(2025, 1, 1),
            expires_date=date(2027, 1, 1),
        )
        verification = Verification(
            checked_at=datetime(2026, 10, 3, 18, 0, 0),
            source="ARRT",
            result="verified",
            details=details or {"status": "Active", "note": "Synthetic test record"},
        )
        credential.verifications.append(verification)
        associate.credentials.append(credential)
        db.add(associate)
        db.commit()
        return verification.id


def test_evidence_endpoint_returns_pdf_and_persists_path(client):
    verification_id = add_verification()

    response = client.get("/api/evidence/%d.pdf" % verification_id)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="verification-%d.pdf"' % verification_id in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    with SessionLocal() as db:
        verification = db.scalar(select(Verification).where(Verification.id == verification_id))
        assert verification.evidence_path == str(evidence.EVIDENCE_DIR / ("verification-%d.pdf" % verification_id))
        assert (evidence.EVIDENCE_DIR / ("verification-%d.pdf" % verification_id)).is_file()


def test_evidence_endpoint_returns_404_for_unknown_verification(client):
    response = client.get("/api/evidence/999999.pdf")

    assert response.status_code == 404
    assert response.json()["detail"] == "Verification not found"


def test_evidence_pdf_escapes_html_in_details(client, monkeypatch):
    verification_id = add_verification(details={"note": "<script>alert('x')</script>"})
    rendered_documents = []

    def capture_render(document, output_path):
        rendered_documents.append(document)
        output_path.write_bytes(b"%PDF-1.4\nsynthetic test PDF\n%%EOF")

    monkeypatch.setattr(evidence, "_render_pdf", capture_render)
    response = client.get("/api/evidence/%d.pdf" % verification_id)

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert "&lt;script&gt;" in rendered_documents[0]
