"""Recording a lookup done by hand, using the invented roster fixture."""
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import seed
from db import Base, SessionLocal, engine
from main import app
from models import Alert, Associate, Credential

FIXTURE = Path(__file__).parent / "fixtures" / "roster.csv"


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    seed.seed(reset=True, roster_path=str(FIXTURE))
    with TestClient(app) as c:
        yield c


def credential_id(name="Blake Testperson") -> int:
    with SessionLocal() as db:
        return db.scalar(select(Credential.id).join(Associate).where(Associate.name == name))


def in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def test_recording_a_verified_lookup_updates_the_credential(client):
    cid = credential_id()
    response = client.post("/api/verify/credential/%d/manual" % cid, json={
        "result": "verified", "number": " 123456 ", "expires_date": in_days(400), "note": "Checked on arrt.org",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "verified" and body["source"] == "ARRT"
    assert body["details"] == {
        "entered_by_hand": True, "number": "123456", "expires_date": in_days(400), "note": "Checked on arrt.org",
    }
    detail = client.get("/api/credentials", params={"status": "valid"}).json()
    assert [(c["id"], c["number"], c["expires_date"], c["status"]) for c in detail] == [
        (cid, "123456", in_days(400), "valid")
    ]


@pytest.mark.parametrize("days, status", [(20, "expiring_30"), (75, "expiring_90"), (-3, "expired")])
def test_status_follows_the_entered_date(client, days, status):
    cid = credential_id()
    client.post("/api/verify/credential/%d/manual" % cid, json={"result": "verified", "expires_date": in_days(days)})
    with SessionLocal() as db:
        assert db.get(Credential, cid).status == status


def test_entered_dates_drive_alerts(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    cid = credential_id()
    client.post("/api/verify/credential/%d/manual" % cid, json={"result": "verified", "expires_date": in_days(20)})
    assert client.post("/api/alerts/run").json()["by_threshold"] == {"30": 2}
    with SessionLocal() as db:
        assert {a.credential_id for a in db.scalars(select(Alert))} == {cid}


def test_not_found_is_recorded_without_touching_the_credential(client):
    cid = credential_id()
    body = client.post("/api/verify/credential/%d/manual" % cid, json={"result": "not_found"}).json()
    assert body["result"] == "not_found" and body["details"]["entered_by_hand"] is True
    with SessionLocal() as db:
        credential = db.get(Credential, cid)
        assert (credential.status, credential.number, credential.expires_date) == ("verification_failed", None, None)


def test_validation(client):
    cid = credential_id()
    url = "/api/verify/credential/%d/manual" % cid
    missing = client.post(url, json={"result": "verified", "number": "123"})
    assert missing.status_code == 422 and "expiry date is required" in missing.json()["detail"]
    assert client.post(url, json={"result": "excluded"}).status_code == 422
    assert client.post(url, json={"result": "verified", "expires_date": "soon"}).status_code == 422
    backwards = client.post(url, json={"result": "verified", "expires_date": in_days(10), "issued_date": in_days(20)})
    assert backwards.status_code == 422
    assert client.post("/api/verify/credential/99999/manual", json={"result": "not_found"}).status_code == 404
    with SessionLocal() as db:
        assert db.get(Credential, cid).status == "unverified"


def test_mock_credentials_cannot_be_entered_by_hand():
    Base.metadata.drop_all(engine)
    seed.seed(reset=True, synthetic=True)
    with TestClient(app) as c:
        refused = c.post("/api/verify/credential/1/manual", json={"result": "verified", "expires_date": in_days(100)})
    assert refused.status_code == 409


def test_entering_a_michigan_license_number_lets_the_automatic_check_run(client, monkeypatch):
    from verify import michigan_lara
    calls = []

    def fetch(first="", last="", number=""):
        calls.append(number)
        return michigan_lara.URL, "Your search returned no results"

    monkeypatch.setattr(michigan_lara, "fetch", fetch)
    with SessionLocal() as db:
        cid = db.scalar(select(Credential.id).where(Credential.credential_type.has(name="Michigan License")))
    client.post("/api/verify/credential/%d/manual" % cid, json={
        "result": "verified", "number": "4700000009", "expires_date": in_days(300),
    })
    client.post("/api/verify/credential/%d" % cid)
    assert calls == ["4700000009"]
