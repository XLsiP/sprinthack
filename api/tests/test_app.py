from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from db import Base, SessionLocal, engine
from main import app, cors_settings
from models import Associate, Credential, CredentialType
from status import refresh_credential
from verify import nppes


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def add_associate(expires_in_days, type_name="ARRT Certification", source="ARRT", npi=None, department="Radiology"):
    with SessionLocal() as db:
        ctype = db.query(CredentialType).filter_by(name=type_name).first() or CredentialType(
            name=type_name, issuing_source=source, verify_method="mock", renewal_months=12
        )
        associate = Associate(
            name="Test Person", npi=npi, role="Radiologic Technologist", department=department,
            facility="Memorial Hospital", state="IN", manager_email="m@example.org",
        )
        expires = None if expires_in_days is None else date.today() + timedelta(days=expires_in_days)
        credential = Credential(credential_type=ctype, number="ARRT-0000001", expires_date=expires)
        refresh_credential(credential)
        associate.credentials.append(credential)
        db.add(associate)
        db.commit()
        return associate.id, credential.id


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_match_license():
    provider = {"basic": {"status": "A"}, "taxonomies": [{"license": "RN-123456", "state": "CA"}]}
    assert nppes.match_license(provider, "rn123456", "CA")
    assert not nppes.match_license(provider, "RN123456", "NY")
    assert not nppes.match_license(provider, None, "CA")


def test_npi_checksum():
    assert nppes.npi_checksum_ok("1234567893")
    assert not nppes.npi_checksum_ok("1234567890")


def test_verify_mock_records_a_verification(client):
    associate_id, credential_id = add_associate(400)
    result = client.post("/api/verify/credential/%d" % credential_id).json()
    assert result["source"] == "ARRT" and result["details"]["mock"] is True

    detail = client.get("/api/associates/%d" % associate_id).json()
    assert detail["credentials"][0]["last_verification"]["id"] == result["id"]
    assert client.post("/api/verify/all").json()["checked"] == 1


def test_verify_uses_npi_registry(client, monkeypatch):
    monkeypatch.setattr(
        nppes, "lookup_npi",
        lambda npi: {
            "basic": {"status": "A", "first_name": "Test", "last_name": "Person"},
            "taxonomies": [{"desc": "Radiologic Technologist"}],
        },
    )
    associate_id, _ = add_associate(None, type_name="NPI Registration", source="NPPES", npi="1234567893")
    results = client.post("/api/verify/associate/%d" % associate_id).json()
    assert results[0]["result"] == "verified"
    assert results[0]["details"]["registry_name"] == "Test Person"
    assert results[0]["details"]["taxonomy_matches_role"] is True


def test_fake_npi_is_not_looked_up(client, monkeypatch):
    monkeypatch.setattr(nppes, "lookup_npi", lambda npi: pytest.fail("should not call the registry"))
    associate_id, credential_id = add_associate(None, type_name="NPI Registration", source="NPPES", npi="1234567890")
    assert client.post("/api/verify/credential/%d" % credential_id).json()["result"] == "not_found"
    assert client.get("/api/associates/%d" % associate_id).json()["worst_status"] == "verification_failed"


def test_cors_settings(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ORIGIN_REGEX", raising=False)
    assert cors_settings() == {"allow_origins": ["http://localhost:3000"], "allow_origin_regex": None}

    monkeypatch.setenv("CORS_ORIGINS", "https://app.vercel.app/, http://localhost:3000,")
    monkeypatch.setenv("CORS_ORIGIN_REGEX", r"https://app-.*\.vercel\.app")
    assert cors_settings() == {
        "allow_origins": ["https://app.vercel.app", "http://localhost:3000"],
        "allow_origin_regex": r"https://app-.*\.vercel\.app",
    }
