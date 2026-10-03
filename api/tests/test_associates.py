from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, CredentialType, Verification
from status import refresh_credential


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def add_associate(name, *expiry_days, department="Radiology", facility="Epworth Hospital",
                  manager="rad@example.org", results=()):
    """One associate with a BLS credential per entry in `expiry_days`; `results` are verifications of the first."""
    with SessionLocal() as db:
        ctype = db.query(CredentialType).filter_by(name="BLS").first() or CredentialType(
            name="BLS", issuing_source="American Heart Association", verify_method="mock", renewal_months=24
        )
        associate = Associate(
            name=name, role="Registered Nurse", department=department, facility=facility, state="IN",
            manager_email=manager,
        )
        for i, days in enumerate(expiry_days):
            credential = Credential(
                credential_type=ctype, number="BLS-%s-%d" % (name, i), expires_date=date.today() + timedelta(days=days)
            )
            if i == 0:
                for day, result in enumerate(results, start=1):
                    credential.verifications.append(Verification(
                        checked_at=datetime(2026, 1, day), source=ctype.issuing_source, result=result, details={}
                    ))
            refresh_credential(credential)
            associate.credentials.append(credential)
        db.add(associate)
        db.commit()
        return associate.id


def names(response):
    return [a["name"] for a in response.json()]


@pytest.fixture
def staff(client):
    return {
        "Avery": add_associate("Avery", 400),
        "Blake": add_associate("Blake", -5, 400),
        "Casey": add_associate("Casey", 20, department="Emergency", manager="ed@example.org"),
        "Devon": add_associate("Devon", 400, facility="Beacon Kalamazoo", results=["excluded"]),
        "Emery": add_associate("Emery", 75, department="Emergency", facility="Beacon Kalamazoo", manager="ed@example.org"),
    }


def test_list_fields(client, staff):
    blake = next(a for a in client.get("/api/associates").json() if a["name"] == "Blake")
    assert blake == {
        "id": staff["Blake"], "name": "Blake", "npi": None, "role": "Registered Nurse", "department": "Radiology",
        "facility": "Epworth Hospital", "state": "IN", "manager_email": "rad@example.org",
        "worst_status": "expired", "credential_count": 2,
    }


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"manager": "ed@example.org"}, ["Casey", "Emery"]),
        ({"department": "Radiology"}, ["Avery", "Blake", "Devon"]),
        ({"facility": "Beacon Kalamazoo"}, ["Devon", "Emery"]),
        ({"status": "expired"}, ["Blake"]),
        ({"status": "valid"}, ["Avery", "Blake"]),  # Blake has one expired and one valid credential
        ({"status": ["expired", "excluded"]}, ["Blake", "Devon"]),
        ({"department": "Emergency", "facility": "Beacon Kalamazoo"}, ["Emery"]),
        ({"manager": "rad@example.org", "status": "excluded"}, ["Devon"]),
        ({"facility": "Nowhere"}, []),
    ],
)
def test_filters(client, staff, params, expected):
    response = client.get("/api/associates", params={**params, "sort": "name"})
    assert names(response) == expected
    assert response.headers["X-Total-Count"] == str(len(expected))


def test_invalid_parameters_are_rejected(client, staff):
    assert client.get("/api/associates", params={"status": "bogus"}).status_code == 422
    assert client.get("/api/associates", params={"sort": "bogus"}).status_code == 422
    assert client.get("/api/associates", params={"limit": 0}).status_code == 422


def test_sort(client, staff):
    assert names(client.get("/api/associates")) == ["Devon", "Blake", "Casey", "Emery", "Avery"]
    assert names(client.get("/api/associates", params={"sort": "name"})) == ["Avery", "Blake", "Casey", "Devon", "Emery"]


def test_associate_without_credentials_sorts_last(client, staff):
    add_associate("Aaron")
    listed = client.get("/api/associates").json()
    assert listed[-1]["name"] == "Aaron"
    assert listed[-1]["worst_status"] is None and listed[-1]["credential_count"] == 0


def test_paging_and_total(client, staff):
    first = client.get("/api/associates", params={"sort": "name", "limit": 2})
    second = client.get("/api/associates", params={"sort": "name", "limit": 2, "offset": 2})
    last = client.get("/api/associates", params={"sort": "name", "limit": 2, "offset": 4})
    assert [names(r) for r in (first, second, last)] == [["Avery", "Blake"], ["Casey", "Devon"], ["Emery"]]
    assert {r.headers["X-Total-Count"] for r in (first, second, last)} == {"5"}


def test_total_header_is_readable_cross_origin(client, staff):
    response = client.get("/api/associates", headers={"Origin": "http://localhost:3000"})
    assert "X-Total-Count" in response.headers["access-control-expose-headers"]


def test_detail(client, staff):
    detail = client.get("/api/associates/%d" % staff["Blake"]).json()
    assert detail["name"] == "Blake" and detail["worst_status"] == "expired"
    assert [c["status"] for c in detail["credentials"]] == ["expired", "valid"]
    credential = detail["credentials"][0]
    assert credential["credential_type"] == "BLS" and credential["days_left"] == -5
    assert credential["last_verification"] is None


def test_detail_has_latest_verification_per_credential(client):
    associate_id = add_associate("Finley", 400, 400, results=["not_found", "verified"])
    first, second = sorted(client.get("/api/associates/%d" % associate_id).json()["credentials"], key=lambda c: c["id"])
    assert first["last_verification"]["result"] == "verified"
    assert first["last_verification"]["checked_at"] == "2026-01-02T00:00:00"
    assert first["status"] == "valid"
    assert second["last_verification"] is None


def test_detail_not_found(client):
    assert client.get("/api/associates/999").status_code == 404
    assert client.get("/api/associates/abc").status_code == 422
