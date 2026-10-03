from datetime import date, datetime

import pytest

from models import Associate, Credential, Verification
from verify.arrt import ArrtVerifier
from verify.bls import BlsVerifier
from verify.indiana_license import IndianaLicenseVerifier
from verify.michigan_license import MichiganLicenseVerifier
from verify.mock import MockVerifier, mock_outcome


def make_inputs(number="ARRT-0000001"):
    associate = Associate(name="Jordan Reyes")
    credential = Credential(number=number, expires_date=date(2030, 1, 1))
    return associate, credential


@pytest.mark.parametrize(
    ("verifier_type", "source"),
    [
        (ArrtVerifier, "ARRT"),
        (IndianaLicenseVerifier, "Indiana PLA"),
        (MichiganLicenseVerifier, "Michigan LARA"),
        (BlsVerifier, "American Heart Association"),
    ],
)
def test_source_verifiers_are_labeled_mock_and_report_their_source(verifier_type, source, monkeypatch):
    monkeypatch.setattr("verify.mock.pause", lambda: None)
    associate, credential = make_inputs()

    result = verifier_type().verify(associate, credential)

    assert result.source == source
    assert result.details["mock"] is True
    assert result.result == mock_outcome(credential.number)


@pytest.mark.parametrize(
    ("seeded_result", "expected_result"),
    [("verified", "verified"), ("not_found", "not_found")],
)
def test_mock_verifier_uses_seeded_mock_outcome(seeded_result, expected_result, monkeypatch):
    monkeypatch.setattr("verify.mock.pause", lambda: None)
    associate, credential = make_inputs()
    credential.verifications.append(
        Verification(
            checked_at=datetime(2026, 1, 1),
            source="ARRT",
            result=seeded_result,
            details={"mock": True, "seeded": True},
        )
    )
    monkeypatch.setattr(
        "verify.mock.mock_outcome",
        lambda number: pytest.fail("seeded outcome should be used"),
    )

    result = MockVerifier().verify(associate, credential)

    assert result.result == expected_result
    assert result.details["outcome_source"] == "seed"


def test_mock_verifier_falls_back_to_deterministic_outcome(monkeypatch):
    monkeypatch.setattr("verify.mock.pause", lambda: None)
    associate, credential = make_inputs()

    first = MockVerifier().verify(associate, credential)
    second = MockVerifier().verify(associate, credential)

    assert first.result == second.result == mock_outcome(credential.number)
    assert first.details["outcome_source"] == "deterministic_mock"


def test_mock_verifier_requires_a_credential_number(monkeypatch):
    monkeypatch.setattr("verify.mock.pause", lambda: None)
    associate, credential = make_inputs(number=None)

    result = MockVerifier().verify(associate, credential)

    assert result.result == "not_found"
    assert result.details["reason"] == "No number on file"
    assert result.details["mock"] is True


def test_pause_uses_short_delay_and_can_be_skipped(monkeypatch):
    from verify import mock

    sleeps = []
    monkeypatch.setattr(mock, "MOCK_DELAY_SECONDS", 0.4)
    monkeypatch.setattr(mock.time, "sleep", sleeps.append)

    mock.pause()
    assert sleeps == [0.4]

    token = mock.skip_delay.set(True)
    try:
        mock.pause()
    finally:
        mock.skip_delay.reset(token)
    assert sleeps == [0.4]
