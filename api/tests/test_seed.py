from collections import Counter
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import seed
from db import SessionLocal
from models import Associate, Credential, CredentialType
from verify.nppes import npi_checksum_ok

TODAY = date(2026, 1, 15)
ISSUE_TYPES = {
    "Indiana State License", "Michigan State License", "ARRT RT(R)", "ARRT CT", "NMTCB Certification", "BLS",
    "NPI Registration",
}


def load_associates() -> list[Associate]:
    with SessionLocal() as db:
        return list(db.scalars(
            select(Associate).order_by(Associate.id).options(
                selectinload(Associate.credentials).selectinload(Credential.credential_type),
                selectinload(Associate.credentials).selectinload(Credential.verifications),
            )
        ))


@pytest.fixture(scope="module")
def associates() -> list[Associate]:
    assert seed.seed(reset=True, today=TODAY) == seed.TOTAL_ASSOCIATES
    return load_associates()


@pytest.fixture(scope="module")
def team(associates) -> list[Associate]:
    return [a for a in associates if a.manager_email == seed.DEMO_MANAGER]


def test_all_facilities_are_staffed(associates):
    assert len(associates) == 1500
    assert {(a.facility, a.state) for a in associates} == set(seed.FACILITIES)
    assert len(seed.FACILITIES) == 11 and {state for _, state in seed.FACILITIES} == {"IN", "MI"}


def test_radiology_team_is_sixty_under_one_manager(associates, team):
    assert len(team) == 60
    demo_department = [
        a for a in associates if a.department == "Radiology" and a.facility == seed.DEMO_FACILITY
    ]
    assert demo_department == team


def test_credential_types():
    with SessionLocal() as db:
        names = set(db.scalars(select(CredentialType.name)))
    assert names == ISSUE_TYPES | {"OIG Exclusion Check"}


def test_team_covers_every_status(team):
    statuses = Counter(c.status for a in team for c in a.credentials)
    for status in ("valid", "expiring_30", "expiring_60", "expiring_90", "expired", "verification_failed"):
        assert statuses[status] > 0, status
    assert statuses["excluded"] == 1


def test_one_npi_mismatch_on_the_team(associates):
    mismatched = [
        a for a in associates for c in a.credentials for v in c.verifications
        if v.result == "mismatch" and c.credential_type.name == "NPI Registration"
    ]
    assert len(mismatched) == 1
    assert mismatched[0].manager_email == seed.DEMO_MANAGER and mismatched[0].role == "Radiologist"


def test_one_excluded_associate(associates):
    excluded = [a for a in associates if any(c.status == "excluded" for c in a.credentials)]
    assert len(excluded) == 1 and excluded[0].manager_email == seed.DEMO_MANAGER


def test_associates_hold_what_their_role_requires(associates):
    for a in associates:
        held = {c.credential_type.name for c in a.credentials}
        assert held >= set(seed.ROLES[a.role]) | {seed.STATE_LICENSE[a.state]}, a.name


def test_data_is_synthetic(associates):
    npis = [a.npi for a in associates if a.npi]
    assert npis and not any(npi_checksum_ok(npi) for npi in npis)
    assert all(a.manager_email.endswith("@example.org") for a in associates)


def test_seed_is_deterministic(associates):
    def snapshot(rows):
        return [(a.name, a.npi, a.role, a.facility, [(c.number, c.expires_date) for c in a.credentials]) for a in rows]

    seed.seed(reset=True, today=TODAY)
    assert snapshot(load_associates()) == snapshot(associates)


def test_seed_refuses_a_populated_database(associates):
    with pytest.raises(SystemExit):
        seed.seed(reset=False, today=TODAY)


def test_no_credential_is_issued_in_the_future(associates):
    future = [(a.name, c.credential_type.name) for a in associates for c in a.credentials
              if c.issued_date and c.issued_date > TODAY]
    assert future == []


def test_issue_and_expiry_are_one_renewal_period_apart(associates):
    for a in associates:
        for c in a.credentials:
            if c.expires_date is None:
                assert c.issued_date is None
                continue
            months = c.credential_type.renewal_months
            assert c.expires_date - c.issued_date == timedelta(days=months * 30), (a.name, c.credential_type.name)
