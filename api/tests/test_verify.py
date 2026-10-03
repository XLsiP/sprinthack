from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, CredentialType, Verification
from status import refresh_credential
from verify import VERIFIERS
from verify.base import VerificationResult


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


def add_associate(
    name: str,
    *credential_numbers: str,
    department: str = "Radiology",
    facility: str = "Epworth Hospital",
    manager: str = "rad@example.org",
) -> int:
    with SessionLocal() as db:
        credential_type = db.scalar(select(CredentialType).where(CredentialType.name == "ARRT RT(R)"))
        if credential_type is None:
            credential_type = CredentialType(
                name="ARRT RT(R)", issuing_source="ARRT", verify_method="mock", renewal_months=12
            )
        associate = Associate(
            name=name,
            role="Radiologic Technologist",
            department=department,
            facility=facility,
            state="IN",
            manager_email=manager,
        )
        for number in credential_numbers:
            credential = Credential(
                credential_type=credential_type,
                number=number,
                expires_date=date.today() + timedelta(days=365),
            )
            refresh_credential(credential)
            associate.credentials.append(credential)
        db.add(associate)
        db.commit()
        return associate.id


class NumberResultVerifier:
    source = "ARRT"

    def verify(self, associate: Associate, credential: Credential) -> VerificationResult:
        result = "not_found" if credential.number.endswith("missing") else "verified"
        return VerificationResult(result, self.source, {"credential_number": credential.number, "mock": True})


@pytest.fixture
def deterministic_verifier(monkeypatch):
    monkeypatch.setitem(VERIFIERS, "ARRT", NumberResultVerifier())


def test_verify_credential_persists_result(client, deterministic_verifier):
    associate_id = add_associate("Jordan Reyes", "RT-001")
    with SessionLocal() as db:
        credential_id = db.scalar(select(Credential.id))

    response = client.post("/api/verify/credential/%d" % credential_id)

    assert response.status_code == 200
    body = response.json()
    assert body["credential_id"] == credential_id
    assert body["source"] == "ARRT"
    assert body["result"] == "verified"
    assert body["details"] == {"credential_number": "RT-001", "mock": True}

    with SessionLocal() as db:
        verification = db.scalar(select(Verification).where(Verification.credential_id == credential_id))
        assert verification is not None
        assert verification.id == body["id"]
        assert verification.credential.associate_id == associate_id


def test_verify_associate_persists_a_result_for_each_credential(client, deterministic_verifier):
    associate_id = add_associate("Jordan Reyes", "RT-001", "RT-002-missing")

    response = client.post("/api/verify/associate/%d" % associate_id)

    assert response.status_code == 200
    assert [item["result"] for item in response.json()] == ["verified", "not_found"]
    with SessionLocal() as db:
        rows = list(db.scalars(
            select(Verification)
            .join(Credential)
            .where(Credential.associate_id == associate_id)
            .order_by(Credential.number)
        ))
        assert len(rows) == 2
        assert [row.result for row in rows] == ["verified", "not_found"]


def test_verify_all_counts_and_persists_only_filtered_credentials(client, deterministic_verifier):
    add_associate("Jordan Reyes", "RAD-verified", department="Radiology")
    add_associate("Casey Nguyen", "RAD-missing", department="Radiology")
    add_associate("Avery Blake", "ED-verified", department="Emergency", manager="ed@example.org")

    response = client.post("/api/verify/all", params={"department": "Radiology"})

    assert response.status_code == 200
    assert response.json() == {
        "checked": 2, "by_result": {"verified": 1, "not_found": 1}, "skipped_manual": 0,
    }
    with SessionLocal() as db:
        rows = list(db.scalars(select(Verification)))
        assert len(rows) == 2
        assert all(row.credential.associate.department == "Radiology" for row in rows)


def test_verify_all_empty_scope_returns_zero_counts(client, deterministic_verifier):
    add_associate("Jordan Reyes", "RT-001", department="Radiology")

    response = client.post("/api/verify/all", params={"department": "Emergency"})

    assert response.status_code == 200
    assert response.json() == {"checked": 0, "by_result": {}, "skipped_manual": 0}
    with SessionLocal() as db:
        assert db.scalar(select(Verification.id)) is None


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("/api/verify/credential/999999", "Credential not found"),
        ("/api/verify/associate/999999", "Associate not found or has no credentials"),
    ],
)
def test_verify_missing_resource_returns_404(client, path, message):
    response = client.post(path)

    assert response.status_code == 404
    assert response.json()["detail"] == message


def test_verify_associate_without_credentials_returns_404(client):
    with SessionLocal() as db:
        associate = Associate(
            name="No Credentials",
            role="Radiologic Technologist",
            department="Radiology",
            facility="Epworth Hospital",
            state="IN",
            manager_email="rad@example.org",
        )
        db.add(associate)
        db.commit()
        associate_id = associate.id

    response = client.post("/api/verify/associate/%d" % associate_id)

    assert response.status_code == 404
    assert response.json()["detail"] == "Associate not found or has no credentials"
