from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import scheduler
from db import Base, SessionLocal, engine
from main import app
from models import Alert, Associate, Credential, CredentialType, Verification


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    scheduler._last_run = None
    with TestClient(app) as c:
        yield c
    scheduler.shutdown()


def add_credential(expires_in_days: int, stored_status: str = "valid") -> int:
    with SessionLocal() as db:
        ctype = db.query(CredentialType).filter_by(name="BLS").first() or CredentialType(
            name="BLS", issuing_source="American Heart Association", verify_method="mock", renewal_months=24
        )
        associate = Associate(
            name="Test Person", role="Registered Nurse", department="Emergency", facility="Epworth Hospital",
            state="IN", manager_email="manager@example.org",
        )
        credential = Credential(
            credential_type=ctype, number="BLS-%d" % expires_in_days,
            expires_date=date.today() + timedelta(days=expires_in_days), status=stored_status,
        )
        associate.credentials.append(credential)
        db.add(associate)
        db.commit()
        return credential.id


def count(model) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model))


def test_run_reverifies_every_credential(client):
    for days in (400, 200, 20):
        add_credential(days)

    result = scheduler.run_daily_job("manual")

    assert result.trigger == "manual" and result.checked == 3
    assert sum(result.by_result.values()) == 3
    assert result.finished_at >= result.started_at
    assert count(Verification) == 3


def test_run_refreshes_stale_statuses(client):
    credential_id = add_credential(-1, stored_status="valid")  # expired since its status was stored
    scheduler.run_daily_job()
    with SessionLocal() as db:
        assert db.get(Credential, credential_id).status == "expired"


def test_run_sends_alerts_once(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    add_credential(20)
    add_credential(400)

    first = scheduler.run_daily_job()
    assert first.alerts_skipped is None
    assert first.alerts.sent == 2 and first.alerts.by_threshold == {"30": 2}
    with SessionLocal() as db:
        assert set(db.scalars(select(Alert.sent_to))) == {"manager@example.org", "hr@example.org"}

    second = scheduler.run_daily_job()
    assert second.checked == 2 and second.alerts.sent == 0
    assert count(Alert) == 2


def test_run_without_hr_email_skips_alerts_but_still_verifies(client, monkeypatch):
    monkeypatch.delenv("HR_EMAIL", raising=False)
    add_credential(20)

    result = scheduler.run_daily_job()

    assert result.checked == 1
    assert result.alerts is None and result.alerts_skipped == "HR_EMAIL is not configured"
    assert count(Alert) == 0 and count(Verification) == 1


def test_endpoints(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    add_credential(20)

    before = client.get("/api/jobs/daily").json()
    assert before == {"enabled": False, "next_run_at": None, "running": False, "last_run": None}

    run = client.post("/api/jobs/daily/run")
    assert run.status_code == 200
    body = run.json()
    assert body["trigger"] == "manual" and body["checked"] == 1 and body["alerts"]["sent"] == 2

    assert client.get("/api/jobs/daily").json()["last_run"] == body


def test_overlapping_run_is_rejected(client):
    assert scheduler._lock.acquire(blocking=False)
    try:
        assert client.get("/api/jobs/daily").json()["running"] is True
        assert client.post("/api/jobs/daily/run").status_code == 409
        with pytest.raises(scheduler.AlreadyRunning):
            scheduler.run_daily_job()
    finally:
        scheduler._lock.release()
    assert client.post("/api/jobs/daily/run").status_code == 200


def test_start_registers_one_daily_job(client, monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "1")
    monkeypatch.setenv("DAILY_JOB_HOUR", "5")
    monkeypatch.setenv("DAILY_JOB_MINUTE", "30")
    monkeypatch.setenv("SCHEDULER_TIMEZONE", "America/Indiana/Indianapolis")

    scheduler.start()
    scheduler.start()  # a second call must not add a second scheduler or job

    jobs = scheduler._scheduler.get_jobs()
    assert [job.id for job in jobs] == [scheduler.JOB_ID]
    fields = {field.name: str(field) for field in jobs[0].trigger.fields}
    assert fields["hour"] == "5" and fields["minute"] == "30" and fields["day"] == "*"
    assert str(jobs[0].trigger.timezone) == "America/Indiana/Indianapolis"

    status = client.get("/api/jobs/daily").json()
    assert status["enabled"] is True and status["next_run_at"] is not None

    scheduler.shutdown()
    assert client.get("/api/jobs/daily").json()["enabled"] is False


def test_start_does_nothing_when_disabled(client, monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "0")
    scheduler.start()
    assert scheduler._scheduler is None


def test_scheduled_run_records_trigger_and_survives_failure(client, monkeypatch):
    add_credential(400)
    scheduler._scheduled_run()
    assert scheduler.status().last_run.trigger == "scheduled"

    def boom(*args, **kwargs):
        raise RuntimeError("source exploded")

    monkeypatch.setattr(scheduler.verify, "run", boom)
    scheduler._scheduled_run()  # logged, not raised, so the scheduler thread keeps going
    assert not scheduler._lock.locked()
