from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from db import Base, SessionLocal, engine
from main import app
from models import Alert, Associate, Credential, CredentialEmailContact, CredentialType, RoleRequirement, Verification

# The data model contract from CLAUDE.md.
CONTRACT = {
    "associates": {"id", "name", "npi", "role", "department", "facility", "state", "manager_email"},
    "credential_types": {"id", "name", "issuing_source", "verify_method", "renewal_months"},
    "role_requirements": {"role", "credential_type_id"},
    "credentials": {"id", "associate_id", "credential_type_id", "number", "issued_date", "expires_date", "status"},
    "verifications": {"id", "credential_id", "checked_at", "source", "result", "details", "evidence_path"},
    "alerts": {"id", "credential_id", "threshold", "sent_to", "sent_at", "channel"},
    "credential_email_contacts": {"id", "credential_id", "kind", "sent_to", "sent_at", "channel"},
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


def test_startup_adds_indexes_to_existing_tables(db):
    index_names = {
        "ix_associates_manager_department_facility",
        "ix_credentials_status_expires_date",
    }
    with engine.begin() as connection:
        for name in index_names:
            connection.exec_driver_sql("DROP INDEX %s" % name)

    with TestClient(app):
        existing_indexes = {
            index["name"]
            for table in ("associates", "credentials")
            for index in inspect(engine).get_indexes(table)
        }

    assert index_names <= existing_indexes


def test_compound_indexes_cover_scope_and_expiry_filters(db):
    indexes = {
        table: {index["name"]: index["column_names"] for index in inspect(engine).get_indexes(table)}
        for table in ("associates", "credentials")
    }

    assert indexes["associates"]["ix_associates_manager_department_facility"] == [
        "manager_email", "department", "facility",
    ]
    assert indexes["credentials"]["ix_credentials_status_expires_date"] == ["status", "expires_date"]


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
    credential.email_contacts.append(
        CredentialEmailContact(
            kind="initial", sent_to="m@example.org", sent_at=datetime(2025, 12, 3), channel="outbox"
        )
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
    assert loaded.credentials[0].email_contacts[0].kind == "initial"
    assert db.scalar(select(RoleRequirement)).credential_type_id == ctype.id

    db.delete(loaded)
    db.commit()
    for model in (Credential, Verification, Alert, CredentialEmailContact):
        assert db.scalars(select(model)).all() == []
    assert db.scalar(select(CredentialType)) is not None


def test_foreign_keys_are_enforced(db):
    ctype = CredentialType(name="BLS", issuing_source="American Heart Association", verify_method="mock")
    db.add(ctype)
    db.flush()
    db.add(Credential(associate_id=999, credential_type_id=ctype.id))
    with pytest.raises(IntegrityError):
        db.commit()
