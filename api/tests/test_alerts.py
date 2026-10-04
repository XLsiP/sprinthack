from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import mailer
from db import Base, SessionLocal, engine
from main import app
from models import Alert, Associate, Credential, CredentialEmailContact, CredentialType, Verification


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


def add_credential(name: str, days_left: int | None, verification_result: str | None = None) -> int:
    with SessionLocal() as db:
        credential_type = CredentialType(
            name="Test Credential " + name,
            issuing_source="Test",
            verify_method="mock",
            renewal_months=12,
        )
        associate = Associate(
            name=name,
            role="Radiologic Technologist",
            department="Radiology",
            facility="Epworth Hospital",
            state="IN",
            manager_email="manager@example.org",
        )
        credential = Credential(
            credential_type=credential_type,
            number="TEST-" + name,
            expires_date=date.today() + timedelta(days=days_left) if days_left is not None else None,
        )
        if verification_result is not None:
            credential.verifications.append(
                Verification(
                    checked_at=datetime.now(),
                    source="OIG",
                    result=verification_result,
                    details={},
                )
            )
        associate.credentials.append(credential)
        db.add(associate)
        db.commit()
        return credential.id


def test_run_queues_each_due_threshold_for_manager_and_hr(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    for name, days, result in (
        ("Ninety", 90, None),
        ("Sixty", 60, None),
        ("Thirty", 30, None),
        ("ExpiresToday", 0, None),
        ("Expired", -1, None),
        ("Excluded", 120, "excluded"),
    ):
        add_credential(name, days, result)

    response = client.post("/api/alerts/run")

    assert response.status_code == 200
    assert response.json() == {
        "sent": 12,
        "by_threshold": {"90": 2, "60": 2, "30": 2, "expired": 4, "excluded": 2},
        "by_channel": {"email": 0, "outbox": 12},
    }
    alerts_response = client.get("/api/alerts")
    assert alerts_response.status_code == 200
    outbox = alerts_response.json()
    assert len(outbox) == 12
    assert {row["sent_to"] for row in outbox} == {"manager@example.org", "hr@example.org"}
    assert {row["threshold"] for row in outbox} == {"90", "60", "30", "expired", "excluded"}
    assert all(row["channel"] == "outbox" for row in outbox)


def test_run_does_not_backfill_missed_thresholds_or_alert_non_expiring_credentials(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    add_credential("WithinThirty", 20)
    add_credential("NonExpiring", None)

    response = client.post("/api/alerts/run")

    assert response.status_code == 200
    assert response.json() == {"sent": 2, "by_threshold": {"30": 2}, "by_channel": {"email": 0, "outbox": 2}}
    with SessionLocal() as db:
        assert set(db.scalars(select(Alert.threshold))) == {"30"}


def test_run_is_idempotent_per_credential_and_threshold(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    add_credential("Idempotent", 30)

    first = client.post("/api/alerts/run")
    second = client.post("/api/alerts/run")

    assert first.json() == {"sent": 2, "by_threshold": {"30": 2}, "by_channel": {"email": 0, "outbox": 2}}
    assert second.json() == {"sent": 0, "by_threshold": {}, "by_channel": {"email": 0, "outbox": 0}}
    with SessionLocal() as db:
        assert len(db.scalars(select(Alert)).all()) == 2


def test_run_requires_hr_email(client, monkeypatch):
    monkeypatch.delenv("HR_EMAIL", raising=False)
    add_credential("MissingHR", 30)

    response = client.post("/api/alerts/run")

    assert response.status_code == 503
    assert response.json()["detail"] == "HR_EMAIL must be configured to run alert sweeps"
    with SessionLocal() as db:
        assert db.scalars(select(Alert)).all() == []


def test_email_credential_tracks_initial_and_follow_up(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("ALERT_EMAIL_OVERRIDE_TO", "demo@beaconhealth.org")
    monkeypatch.setattr(mailer, "send", lambda *_args, **_kwargs: None)
    credential_id = add_credential("Contacted", 20)

    first = client.post("/api/alerts/credential/%d/email" % credential_id)

    assert first.status_code == 200
    assert first.json()["kind"] == "initial"
    assert first.json()["channel"] == "email"
    credentials = client.get("/api/credentials?limit=200").json()
    contacted = next(item for item in credentials if item["id"] == credential_id)
    assert contacted["email_contacted"] is True
    assert contacted["email_contact_count"] == 1
    assert contacted["last_email_contact_channel"] == "email"

    second = client.post("/api/alerts/credential/%d/email" % credential_id)

    assert second.status_code == 200
    assert second.json()["kind"] == "follow_up"
    with SessionLocal() as db:
        contacts = db.scalars(select(CredentialEmailContact)).all()
        assert [contact.kind for contact in contacts] == ["initial", "follow_up"]
        assert all(contact.sent_to == "manager@example.org" for contact in contacts)


def test_email_credential_records_outbox_when_not_configured(client, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    credential_id = add_credential("OutboxContact", 20)

    response = client.post("/api/alerts/credential/%d/email" % credential_id)

    assert response.status_code == 200
    assert response.json()["kind"] == "initial"
    assert response.json()["channel"] == "outbox"


def test_email_credential_rejects_missing_or_not_due_credential(client):
    missing = client.post("/api/alerts/credential/999/email")
    valid_id = add_credential("NotDue", 180)
    not_due = client.post("/api/alerts/credential/%d/email" % valid_id)

    assert missing.status_code == 404
    assert not_due.status_code == 409
