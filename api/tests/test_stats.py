from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, CredentialType, Verification
from status import SEVERITY, refresh_credential


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def add_associate(*expiry_days, department="Radiology", facility="Epworth Hospital", manager="rad@example.org",
                  result=None):
    """One associate with a BLS credential per entry in `expiry_days`, each verified with `result` if given."""
    with SessionLocal() as db:
        ctype = db.query(CredentialType).filter_by(name="BLS").first() or CredentialType(
            name="BLS", issuing_source="American Heart Association", verify_method="mock", renewal_months=24
        )
        associate = Associate(
            name="Test Person", role="Registered Nurse", department=department, facility=facility, state="IN",
            manager_email=manager,
        )
        for days in expiry_days:
            credential = Credential(credential_type=ctype, expires_date=date.today() + timedelta(days=days))
            if result:
                credential.verifications.append(Verification(
                    checked_at=datetime(2026, 1, 1), source=ctype.issuing_source, result=result, details={}
                ))
            refresh_credential(credential)
            associate.credentials.append(credential)
        db.add(associate)
        db.commit()


def test_empty_database(client):
    stats = client.get("/api/stats").json()
    assert stats["associates"] == 0 and stats["credentials"] == 0 and stats["unverified"] == 0
    assert stats["by_status"] == dict.fromkeys(SEVERITY, 0)
    assert stats["by_facility"] == []
    assert len(stats["timeline"]) == 13 and all(point["count"] == 0 for point in stats["timeline"])


def test_counts_by_status_and_facility(client):
    add_associate(400, -5)
    add_associate(20, result="verified")
    add_associate(400, facility="Beacon Kalamazoo", result="excluded")
    add_associate(400, 45, facility="Beacon Kalamazoo", result="not_found")

    stats = client.get("/api/stats").json()
    assert stats["associates"] == 4 and stats["credentials"] == 6
    assert stats["unverified"] == 2
    assert stats["by_status"] == {
        "excluded": 1, "expired": 1, "verification_failed": 2, "expiring_30": 1, "expiring_60": 0,
        "expiring_90": 0, "unverified": 0, "valid": 1,
    }
    assert sum(stats["by_status"].values()) == stats["credentials"]

    kalamazoo, epworth = stats["by_facility"]  # sorted by facility name
    assert (kalamazoo["facility"], kalamazoo["total"]) == ("Beacon Kalamazoo", 3)
    assert kalamazoo["by_status"]["excluded"] == 1 and kalamazoo["by_status"]["verification_failed"] == 2
    assert (epworth["facility"], epworth["total"]) == ("Epworth Hospital", 3)
    assert set(epworth["by_status"]) == set(SEVERITY) and epworth["by_status"]["expiring_60"] == 0


def test_timeline_covers_the_next_90_days_by_week(client):
    add_associate(-1, 0, 6, 7, 89, 90, 91, 400)
    timeline = client.get("/api/stats").json()["timeline"]

    today = date.today()
    assert len(timeline) == 13
    assert timeline[0]["start"] == today.isoformat()
    assert timeline[-1]["end"] == (today + timedelta(days=90)).isoformat()
    for week, following in zip(timeline, timeline[1:]):  # contiguous, no gaps or overlap
        assert date.fromisoformat(following["start"]) == date.fromisoformat(week["end"]) + timedelta(days=1)

    counts = [point["count"] for point in timeline]
    assert counts[0] == 2  # day 0 and day 6
    assert counts[1] == 1  # day 7
    assert counts[12] == 2  # day 89 and day 90
    assert sum(counts) == 5  # yesterday, day 91 and day 400 are outside the window


def test_filters_scope_every_number(client):
    add_associate(10, -5)
    add_associate(10, department="Emergency", manager="ed@example.org")
    add_associate(10, 10, 10, facility="Beacon Kalamazoo", manager="ed@example.org", result="verified")

    def summary(**params):
        stats = client.get("/api/stats", params=params).json()
        return (
            stats["associates"], stats["credentials"], stats["unverified"],
            sum(point["count"] for point in stats["timeline"]), [f["facility"] for f in stats["by_facility"]],
        )

    assert summary() == (3, 6, 3, 5, ["Beacon Kalamazoo", "Epworth Hospital"])
    assert summary(manager="rad@example.org") == (1, 2, 2, 1, ["Epworth Hospital"])
    assert summary(manager="ed@example.org") == (2, 4, 1, 4, ["Beacon Kalamazoo", "Epworth Hospital"])
    assert summary(department="Emergency") == (1, 1, 1, 1, ["Epworth Hospital"])
    assert summary(facility="Beacon Kalamazoo") == (1, 3, 0, 3, ["Beacon Kalamazoo"])
    assert summary(facility="Nowhere") == (0, 0, 0, 0, [])


def test_manager_stats_add_up_to_the_overall_counts(client):
    add_associate(5, 400, manager="rad@example.org")
    add_associate(-3, manager="rad@example.org", facility="Beacon Kalamazoo")
    add_associate(200, manager="lab@example.org", department="Laboratory")
    add_associate(manager="empty@example.org")  # a manager whose person has no credentials yet

    rows = client.get("/api/stats/managers").json()
    assert [(r["manager"], r["associates"], r["credentials"]) for r in rows] == [
        ("empty@example.org", 1, 0), ("lab@example.org", 1, 1), ("rad@example.org", 2, 3),
    ]
    overall = client.get("/api/stats").json()
    assert sum(r["associates"] for r in rows) == overall["associates"]
    for status in SEVERITY:
        assert sum(r["by_status"][status] for r in rows) == overall["by_status"][status]
    assert rows[2]["by_status"]["expired"] == 1 and rows[2]["by_status"]["expiring_30"] == 1

    in_kalamazoo = client.get("/api/stats/managers", params={"facility": "Beacon Kalamazoo"}).json()
    assert [(r["manager"], r["associates"], r["credentials"]) for r in in_kalamazoo] == [("rad@example.org", 1, 1)]
    assert client.get("/api/stats/managers", params={"department": "Nowhere"}).json() == []


def test_manager_stats_with_no_data(client):
    assert client.get("/api/stats/managers").json() == []
