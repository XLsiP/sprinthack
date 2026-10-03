from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, CredentialType
from status import refresh_credential


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def add_credential(number, expires_in_days, department="Radiology", facility="Epworth Hospital",
                   manager="rad@example.org"):
    """One associate holding one BLS credential; `expires_in_days=None` means it never expires."""
    with SessionLocal() as db:
        # A credential with no expiry date belongs to a type that never expires, like the OIG check.
        name, months = ("BLS", 24) if expires_in_days is not None else ("OIG Exclusion Check", None)
        ctype = db.query(CredentialType).filter_by(name=name).first() or CredentialType(
            name=name, issuing_source="American Heart Association", verify_method="mock", renewal_months=months
        )
        associate = Associate(
            name="Holder of %s" % number, role="Registered Nurse", department=department, facility=facility,
            state="IN", manager_email=manager,
        )
        expires = None if expires_in_days is None else date.today() + timedelta(days=expires_in_days)
        credential = Credential(credential_type=ctype, number=number, expires_date=expires)
        refresh_credential(credential)
        associate.credentials.append(credential)
        db.add(associate)
        db.commit()


@pytest.fixture
def credentials(client):
    add_credential("valid", 400)
    add_credential("expired", -5)
    add_credential("soon", 20, department="Emergency", manager="ed@example.org")
    add_credential("later", 75, facility="Beacon Kalamazoo")
    add_credential("never", None, department="Emergency", facility="Beacon Kalamazoo", manager="ed@example.org")


def numbers(response):
    return [c["number"] for c in response.json()]


def test_urgent_first_with_fields(client, credentials):
    response = client.get("/api/credentials")
    assert numbers(response) == ["expired", "soon", "later", "valid", "never"]
    first = response.json()[0]
    assert first["status"] == "expired" and first["days_left"] == -5
    assert first["credential_type"] == "BLS" and first["associate_name"] == "Holder of expired"
    assert first["last_verification"] is None
    assert response.json()[-1]["expires_date"] is None and response.json()[-1]["days_left"] is None


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"status": "expired"}, ["expired"]),
        ({"status": ["expiring_30", "expiring_90"]}, ["soon", "later"]),
        ({"status": "excluded"}, []),
        ({"expires_before": in_days(20)}, ["expired"]),  # exclusive of the date itself
        ({"expires_before": in_days(21)}, ["expired", "soon"]),
        ({"expires_before": in_days(1000)}, ["expired", "soon", "later", "valid"]),  # never-expiring left out
        ({"expires_before": in_days(100), "status": "expiring_90"}, ["later"]),
        ({"manager": "ed@example.org"}, ["soon", "never"]),
        ({"department": "Radiology"}, ["expired", "later", "valid"]),
        ({"facility": "Beacon Kalamazoo"}, ["later", "never"]),
        ({"facility": "Beacon Kalamazoo", "department": "Emergency"}, ["never"]),
    ],
)
def test_filters(client, credentials, params, expected):
    response = client.get("/api/credentials", params=params)
    assert numbers(response) == expected
    assert response.headers["X-Total-Count"] == str(len(expected))


def test_invalid_parameters_are_rejected(client, credentials):
    assert client.get("/api/credentials", params={"status": "bogus"}).status_code == 422
    assert client.get("/api/credentials", params={"expires_before": "soon"}).status_code == 422
    assert client.get("/api/credentials", params={"limit": 0}).status_code == 422


def test_paging_and_total(client, credentials):
    pages = [client.get("/api/credentials", params={"limit": 2, "offset": offset}) for offset in (0, 2, 4)]
    assert [numbers(r) for r in pages] == [["expired", "soon"], ["later", "valid"], ["never"]]
    assert {r.headers["X-Total-Count"] for r in pages} == {"5"}
