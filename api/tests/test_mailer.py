import json
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import mailer
from db import Base, SessionLocal, engine
from main import app
from models import Alert, Associate, Credential, CredentialType

HR = "hr@beacon.test.example.org"  # reserved, like every seed address


@pytest.fixture
def client(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    monkeypatch.setenv("HR_EMAIL", HR)
    monkeypatch.setattr(mailer, "PACE_SECONDS", 0)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def resend(monkeypatch):
    """Stand in for the Resend API: records every request, and can be told to fail for an address."""
    class FakeResend:
        def __init__(self):
            self.requests = []
            self.fail_for = {}

        def post(self, url, headers, json, timeout):
            self.requests.append({"url": url, "headers": headers, **json})
            failure = self.fail_for.get(json["to"][0])
            if isinstance(failure, Exception):
                raise failure
            request = httpx.Request("POST", url)
            return httpx.Response(failure or 200, json={"id": "email_%d" % len(self.requests)}, request=request)

    fake = FakeResend()
    monkeypatch.setattr(mailer.httpx, "post", fake.post)
    return fake


def add_credential(name, days_left, manager="manager@beaconhealth.org"):
    with SessionLocal() as db:
        ctype = db.query(CredentialType).filter_by(name="BLS").first() or CredentialType(
            name="BLS", issuing_source="American Heart Association", verify_method="mock", renewal_months=24
        )
        associate = Associate(
            name=name, role="Registered Nurse", department="Emergency", facility="Epworth Hospital", state="IN",
            manager_email=manager,
        )
        associate.credentials.append(Credential(
            credential_type=ctype, number="BLS-" + name, expires_date=date.today() + timedelta(days=days_left)
        ))
        db.add(associate)
        db.commit()


def channels():
    with SessionLocal() as db:
        return {(a.sent_to, a.channel) for a in db.scalars(select(Alert))}


def test_no_api_key_sends_nothing(client, resend):
    add_credential("Avery", 20)
    result = client.post("/api/alerts/run").json()
    assert resend.requests == []
    assert result["by_channel"] == {"email": 0, "outbox": 2}
    assert {channel for _, channel in channels()} == {"outbox"}


def test_sends_one_digest_per_recipient(client, resend, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("HR_EMAIL", "hr@beaconhealth.org")
    add_credential("Avery", 20)
    add_credential("Blake", -3)
    add_credential("Casey", 400)  # not due, so not in any email

    result = client.post("/api/alerts/run").json()

    assert result["sent"] == 4 and result["by_channel"] == {"email": 4, "outbox": 0}
    assert [r["to"] for r in resend.requests] == [["hr@beaconhealth.org"], ["manager@beaconhealth.org"]]
    request = resend.requests[0]
    assert request["url"] == mailer.DEFAULT_API_URL
    assert request["headers"] == {"Authorization": "Bearer re_test_key"}
    assert request["from"] == mailer.DEFAULT_FROM
    assert request["subject"] == "Credential alert: 2 credentials need attention"
    html = request["html"]
    assert "Avery" in html and "Blake" in html and "Casey" not in html
    assert "Expires within 30 days" in html and "Expired" in html and "BLS" in html
    assert html.index("Blake") < html.index("Avery")  # expired before expiring
    assert "http://localhost:3000/associates/" in html
    assert {channel for _, channel in channels()} == {"email"}
    assert {row["channel"] for row in client.get("/api/alerts").json()} == {"email"}


def test_digest_escapes_html():
    credential = Credential(
        associate_id=7, expires_date=date(2026, 1, 1),
        associate=Associate(name="<script>alert(1)</script>", department="R&D", facility="Epworth Hospital"),
        credential_type=CredentialType(name="BLS"),
    )
    subject, html = mailer.render_digest("m@x.org", [(Alert(threshold="30", sent_to="m@x.org"), credential)])
    assert subject == "Credential alert: 1 credential needs attention"
    assert "<script>" not in html and "&lt;script&gt;" in html and "R&amp;D" in html


def test_long_digest_is_summarized():
    def item(i):
        credential = Credential(
            associate_id=i, expires_date=date(2026, 1, 1),
            associate=Associate(name="Person %03d" % i, department="Emergency", facility="Epworth Hospital"),
            credential_type=CredentialType(name="BLS"),
        )
        return Alert(threshold="90", sent_to="hr@x.org"), credential

    _, html = mailer.render_digest("hr@x.org", [item(i) for i in range(60)])
    assert html.count("<tr>") == 1 + mailer.MAX_ROWS and "And 10 more." in html


def test_reserved_addresses_are_not_emailed(client, resend, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    add_credential("Avery", 20, manager="radiology.manager@example.org")

    result = client.post("/api/alerts/run").json()

    assert resend.requests == []
    assert result["by_channel"] == {"email": 0, "outbox": 2}
    assert mailer.is_reserved("a@example.org") and mailer.is_reserved("a@demo.test")
    assert mailer.is_reserved("a@mail.example.com") and not mailer.is_reserved("a@notexample.org")
    assert not mailer.is_reserved("a@beaconhealth.org")


def test_override_redirects_every_digest(client, resend, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("ALERT_EMAIL_OVERRIDE_TO", "demo@beaconhealth.org")
    add_credential("Avery", 20, manager="radiology.manager@example.org")

    result = client.post("/api/alerts/run").json()

    assert [r["to"] for r in resend.requests] == [["demo@beaconhealth.org"]] * 2
    assert resend.requests[1]["subject"].endswith("(for radiology.manager@example.org)")
    assert "Intended recipient: radiology.manager@example.org" in resend.requests[1]["html"]
    assert result["by_channel"] == {"email": 2, "outbox": 0}
    assert channels() == {(HR, "email"), ("radiology.manager@example.org", "email")}  # intended recipient kept


def test_cap_per_run_with_hr_first(client, resend, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("ALERT_EMAIL_OVERRIDE_TO", "demo@beaconhealth.org")
    monkeypatch.setenv("ALERT_EMAIL_MAX_PER_RUN", "2")
    add_credential("Avery", 20, manager="a@example.org")
    add_credential("Blake", 20, manager="b@example.org")
    add_credential("Casey", 20, manager="b@example.org")
    add_credential("Devon", 20, manager="c@example.org")

    result = client.post("/api/alerts/run").json()

    assert len(resend.requests) == 2
    assert "(for %s)" % HR in resend.requests[0]["subject"]
    assert "(for b@example.org)" in resend.requests[1]["subject"]  # the manager with the most alerts
    assert result["by_channel"] == {"email": 6, "outbox": 2}


@pytest.mark.parametrize("failure", [500, 429, httpx.ConnectTimeout("timed out")])
def test_failed_send_stays_in_outbox_and_others_still_go(client, resend, monkeypatch, failure):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("HR_EMAIL", "hr@beaconhealth.org")
    resend.fail_for["hr@beaconhealth.org"] = failure
    add_credential("Avery", 20)

    response = client.post("/api/alerts/run")

    assert response.status_code == 200
    assert response.json()["by_channel"] == {"email": 1, "outbox": 1}
    assert channels() == {("hr@beaconhealth.org", "outbox"), ("manager@beaconhealth.org", "email")}
    assert "re_test_key" not in json.dumps(response.json())


def test_second_sweep_sends_no_email(client, resend, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("HR_EMAIL", "hr@beaconhealth.org")
    add_credential("Avery", 20)

    client.post("/api/alerts/run")
    sent = len(resend.requests)
    second = client.post("/api/alerts/run").json()

    assert sent == 2 and len(resend.requests) == 2
    assert second == {"sent": 0, "by_threshold": {}, "by_channel": {"email": 0, "outbox": 0}}
