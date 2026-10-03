from datetime import date, datetime, timedelta

import pytest

from db import Base, SessionLocal, engine
from models import Associate, Credential, CredentialType, Verification
from status import compute_status, days_left, refresh_credential, refresh_statuses, worst

TODAY = date(2026, 1, 1)


def in_days(days: int) -> date:
    return TODAY + timedelta(days=days)


@pytest.mark.parametrize(
    "expires, last_result, expected",
    [
        (in_days(400), "verified", "valid"),
        (in_days(75), "verified", "expiring_90"),
        (in_days(45), "verified", "expiring_60"),
        (in_days(10), "verified", "expiring_30"),
        (in_days(-5), "verified", "expired"),
        (in_days(400), "not_found", "verification_failed"),
        (in_days(400), "mismatch", "verification_failed"),
        (in_days(400), "excluded", "excluded"),
    ],
)
def test_each_status(expires, last_result, expected):
    assert compute_status(expires, last_result, TODAY) == expected


@pytest.mark.parametrize(
    "days, expected",
    [
        (-1, "expired"),
        (0, "expiring_30"),  # expires today: still valid through the day
        (30, "expiring_30"),
        (31, "expiring_60"),
        (60, "expiring_60"),
        (61, "expiring_90"),
        (90, "expiring_90"),
        (91, "valid"),
    ],
)
def test_day_boundaries(days, expected):
    assert compute_status(in_days(days), None, TODAY) == expected


def test_precedence():
    assert compute_status(in_days(-5), "excluded", TODAY) == "excluded"
    assert compute_status(in_days(-5), "not_found", TODAY) == "expired"
    assert compute_status(in_days(10), "mismatch", TODAY) == "verification_failed"


def test_no_expiry_date():
    assert compute_status(None, None, TODAY) == "valid"
    assert compute_status(None, "verified", TODAY) == "valid"
    assert compute_status(None, "not_found", TODAY) == "verification_failed"
    assert compute_status(None, "excluded", TODAY) == "excluded"
    assert days_left(None, TODAY) is None


def test_unverified_and_error_results_do_not_fail_a_credential():
    assert compute_status(in_days(400), None, TODAY) == "valid"
    assert compute_status(in_days(400), "error", TODAY) == "valid"


def test_worst():
    assert worst(["valid", "expiring_60", "expired", "expiring_30"]) == "expired"
    assert worst(["verification_failed", "excluded"]) == "excluded"
    assert worst(["valid"]) == "valid"
    assert worst([]) is None


def credential_with(*results: str, expires: date = in_days(400)) -> Credential:
    credential = Credential(expires_date=expires)
    for day, result in enumerate(results, start=1):
        credential.verifications.append(Verification(checked_at=datetime(2025, 12, day), source="X", result=result))
    return credential


def test_refresh_credential_uses_the_latest_verification():
    credential = credential_with("not_found", "verified")
    refresh_credential(credential, TODAY)
    assert credential.status == "valid"

    credential = credential_with("verified", "mismatch")
    refresh_credential(credential, TODAY)
    assert credential.status == "verification_failed"

    credential = credential_with()
    refresh_credential(credential, TODAY)
    assert credential.status == "valid"


def test_error_does_not_clear_an_earlier_result():
    for earlier, expected in (("excluded", "excluded"), ("not_found", "verification_failed"), ("verified", "valid")):
        credential = credential_with(earlier, "error", "error")
        refresh_credential(credential, TODAY)
        assert credential.status == expected

    credential = credential_with("error")
    refresh_credential(credential, TODAY)
    assert credential.status == "valid"


def test_refresh_statuses_ages_with_the_calendar():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        associate = Associate(
            name="Test Person", role="Registered Nurse", department="Emergency",
            facility="Epworth Hospital", state="IN", manager_email="m@example.org",
        )
        ctype = CredentialType(name="BLS", issuing_source="American Heart Association", verify_method="mock")
        credential = Credential(credential_type=ctype, expires_date=in_days(100))
        associate.credentials.append(credential)
        db.add(associate)
        db.commit()

        for days_later, expected in ((0, "valid"), (10, "expiring_90"), (40, "expiring_60"), (70, "expiring_30"), (101, "expired")):
            refresh_statuses(db, in_days(days_later))
            db.refresh(credential)
            assert credential.status == expected


def test_unverified_when_an_expiring_credential_has_no_date_and_no_check():
    assert compute_status(None, None, TODAY, expiry_expected=True) == "unverified"
    assert compute_status(None, "error", TODAY, expiry_expected=True) == "valid"  # callers drop errors first
    assert compute_status(None, "verified", TODAY, expiry_expected=True) == "valid"
    assert compute_status(None, "not_found", TODAY, expiry_expected=True) == "verification_failed"
    assert compute_status(None, "excluded", TODAY, expiry_expected=True) == "excluded"
    assert compute_status(in_days(400), None, TODAY, expiry_expected=True) == "valid"  # a date on file is enough
    assert compute_status(None, None, TODAY) == "valid"  # types that never expire are unchanged


def test_refresh_credential_marks_roster_style_credentials_unverified():
    expiring = Credential(credential_type=CredentialType(name="ARRT", renewal_months=12))
    refresh_credential(expiring, TODAY)
    assert expiring.status == "unverified"

    expiring.verifications.append(Verification(checked_at=datetime(2025, 12, 1), source="ARRT", result="error"))
    refresh_credential(expiring, TODAY)
    assert expiring.status == "unverified"  # an unreachable source is not a verification

    never_expires = Credential(credential_type=CredentialType(name="OIG Exclusion Check", renewal_months=None))
    refresh_credential(never_expires, TODAY)
    assert never_expires.status == "valid"


def test_unverified_ranks_between_expiring_and_valid():
    assert worst(["valid", "unverified"]) == "unverified"
    assert worst(["unverified", "expiring_90"]) == "expiring_90"
