from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from db import Base, SessionLocal, engine
from main import app
from models import Alert, Associate, Credential, CredentialType, RoleRequirement, Verification

# The data model contract from CLAUDE.md.
CONTRACT = {
    "associates": {"id", "name", "npi", "role", "department", "facility", "state", "manager_email"},
    "credential_types": {"id", "name", "issuing_source", "verify_method", "renewal_months"},
    "role_requirements": {"role", "credential_type_id"},
    "credentials": {"id", "associate_id", "credential_type_id", "number", "issued_date", "expires_date", "status"},
    "verifications": {"id", "credential_id", "checked_at", "source", "result", "details", "evidence_path"},
    "alerts": {"id", "credential_id", "threshold", "sent_to", "sent_at", "channel"},
}


def columns_by_table() -> dict[str, set[str]]:
    inspector = inspect(engine)
    return {t: {c["name"] for c in inspector.get_columns(t)} for t in inspector.get_table_names()}


@pytest.fixture
def empty_db():
    Base.metadata.drop_all(engine)
    yield


@pytest.fixture
def db(empty_db):
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        yield session


def test_tables_match_contract(db):
    assert columns_by_table() == CONTRACT


def test_startup_creates_tables(empty_db):
    assert columns_by_table() == {}
    with TestClient(app):
        assert columns_by_table() == CONTRACT
    with TestClient(app):  # starting again on an existing database is fine
        assert columns_by_table() == CONTRACT


def test_round_trip_and_cascade_delete(db):
    ctype = CredentialType(name="ARRT Certification", issuing_source="ARRT", verify_method="mock", renewal_months=12)
    associate = Associate(
        name="Test Person", role="Radiologic Technologist", department="Radiology",
        facility="Memorial Hospital", state="IN", manager_email="m@example.org",
    )
    credential = Credential(
        credential_type=ctype, number="ARRT-0000001", issued_date=date(2025, 1, 1), expires_date=date(2026, 1, 1)
    )
    credential.verifications.append(
        Verification(checked_at=datetime(2025, 6, 1), source="ARRT", result="verified", details={"mock": True})
    )
    credential.alerts.append(
        Alert(threshold="30", sent_to="m@example.org", sent_at=datetime(2025, 12, 2), channel="outbox")
    )
    associate.credentials.append(credential)
    db.add(associate)
    db.flush()
    db.add(RoleRequirement(role=associate.role, credential_type_id=ctype.id))
    db.commit()
    db.expire_all()

    loaded = db.scalar(select(Associate))
    assert loaded.npi is None
    assert loaded.credentials[0].credential_type.name == "ARRT Certification"
    assert loaded.credentials[0].status == "valid"
    assert loaded.credentials[0].verifications[0].details == {"mock": True}
    assert loaded.credentials[0].alerts[0].threshold == "30"
    assert db.scalar(select(RoleRequirement)).credential_type_id == ctype.id

    db.delete(loaded)
    db.commit()
    for model in (Credential, Verification, Alert):
        assert db.scalars(select(model)).all() == []
    assert db.scalar(select(CredentialType)) is not None


def test_foreign_keys_are_enforced(db):
    ctype = CredentialType(name="BLS", issuing_source="American Heart Association", verify_method="mock")
    db.add(ctype)
    db.flush()
    db.add(Credential(associate_id=999, credential_type_id=ctype.id))
    with pytest.raises(IntegrityError):
        db.commit()
