from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import verify
from app.alerts import status_for
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRED_DB", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def test_status_buckets():
    today = date(2026, 1, 1)
    assert status_for("2025-12-31", today) == ("expired", -1)
    assert status_for("2026-01-31", today) == ("critical", 30)
    assert status_for("2026-03-01", today) == ("warning", 59)
    assert status_for("2027-01-01", today) == ("ok", 365)


def test_match_license():
    provider = {"basic": {"status": "A"}, "taxonomies": [{"license": "RN-123456", "state": "CA"}]}
    assert verify.match_license(provider, "rn123456", "CA")
    assert not verify.match_license(provider, "RN123456", "NY")
    assert not verify.match_license(provider, None, "CA")
    assert verify.check_credential(provider, {"type": "RN License", "number": "RN123456", "state": "CA"}) == "verified"
    assert verify.check_credential(None, {"type": "RN License", "number": "X", "state": "CA"}) == "npi_not_found"


def test_add_staff_and_alerts(client):
    staff = client.post("/api/staff", json={"name": "Test Nurse", "role": "RN", "email": "n@example.com"}).json()
    soon = (date.today() + timedelta(days=10)).isoformat()
    later = (date.today() + timedelta(days=500)).isoformat()
    for ctype, expires in (("RN License", soon), ("BLS", later)):
        r = client.post("/api/staff/%d/credentials" % staff["id"], json={"type": ctype, "expires_on": expires})
        assert r.status_code == 201

    creds = client.get("/api/credentials").json()
    assert [c["status"] for c in creds] == ["critical", "ok"]

    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["recipients"] == ["n@example.com"]
    assert "RN License expires in 10 days" in alerts[0]["message"]


def test_verify_uses_npi_registry(client, monkeypatch):
    monkeypatch.setattr(
        verify, "lookup_npi",
        lambda npi: {"basic": {"status": "A"}, "taxonomies": [{"license": "A1", "state": "CA"}]},
    )
    staff = client.post("/api/staff", json={"name": "Doc", "role": "MD", "npi": "1234567890"}).json()
    client.post(
        "/api/staff/%d/credentials" % staff["id"],
        json={"type": "Medical License", "number": "A1", "state": "CA", "expires_on": "2030-01-01"},
    )
    result = client.post("/api/staff/%d/verify" % staff["id"]).json()
    assert result["credentials"][0]["verification_status"] == "verified"
