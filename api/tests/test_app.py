from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, CredentialType
from status import derive_status, refresh_credential
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


def test_status_buckets():
    today = date(2026, 1, 1)
    assert derive_status(date(2025, 12, 31), "verified", today) == "expired"
    assert derive_status(date(2026, 1, 31), "verified", today) == "expiring_30"
    assert derive_status(date(2026, 3, 1), None, today) == "expiring_60"
    assert derive_status(date(2026, 4, 1), None, today) == "expiring_90"
    assert derive_status(date(2027, 1, 1), None, today) == "valid"
    assert derive_status(date(2027, 1, 1), "not_found", today) == "verification_failed"
    assert derive_status(date(2027, 1, 1), "error", today) == "valid"
    assert derive_status(None, "excluded", today) == "excluded"


def test_match_license():
    provider = {"basic": {"status": "A"}, "taxonomies": [{"license": "RN-123456", "state": "CA"}]}
    assert nppes.match_license(provider, "rn123456", "CA")
    assert not nppes.match_license(provider, "RN123456", "NY")
    assert not nppes.match_license(provider, None, "CA")


def test_npi_checksum():
    assert nppes.npi_checksum_ok("1234567893")
    assert not nppes.npi_checksum_ok("1234567890")


def test_credentials_are_urgent_first_and_filterable(client):
    add_associate(400)
    add_associate(-5)
    add_associate(20, department="Emergency")

    creds = client.get("/api/credentials").json()
    assert [c["status"] for c in creds] == ["expired", "expiring_30", "valid"]
    assert creds[0]["days_left"] == -5 and creds[0]["last_verification"] is None

    assert len(client.get("/api/credentials", params={"status": "expired"}).json()) == 1
    assert len(client.get("/api/credentials", params={"department": "Emergency"}).json()) == 1
    soon = (date.today() + timedelta(days=30)).isoformat()
    assert len(client.get("/api/credentials", params={"expires_before": soon}).json()) == 2


def test_associates_and_stats(client):
    associate_id, _ = add_associate(-5)
    add_associate(400)

    listed = client.get("/api/associates", params={"status": "expired"}).json()
    assert [a["id"] for a in listed] == [associate_id]
    assert listed[0]["worst_status"] == "expired"

    detail = client.get("/api/associates/%d" % associate_id).json()
    assert detail["credentials"][0]["credential_type"] == "ARRT Certification"
    assert client.get("/api/associates/999").status_code == 404

    stats = client.get("/api/stats").json()
    assert stats["associates"] == 2 and stats["unverified"] == 2
    assert stats["by_status"]["expired"] == 1 and stats["by_status"]["valid"] == 1
    assert len(stats["timeline"]) == 12
    assert client.get("/api/stats", params={"facility": "Nowhere"}).json()["credentials"] == 0


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
