import csv

import pytest

from models import Associate, Credential
from verify import leie

FIELDS = [
    "LASTNAME", "FIRSTNAME", "MIDNAME", "BUSNAME", "GENERAL", "SPECIALTY",
    "UPIN", "NPI", "DOB", "ADDRESS", "CITY", "STATE", "ZIP", "EXCLTYPE",
    "EXCLDATE", "REINDATE", "WAIVERDATE", "WVRSTATE",
]


@pytest.fixture(autouse=True)
def clear_leie_cache():
    leie.load_leie_records.cache_clear()
    yield
    leie.load_leie_records.cache_clear()


def write_csv(path, rows, fields=FIELDS):
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def exclusion(first="Jordan", last="Reyes", npi="1234567893", **overrides):
    row = {
        "FIRSTNAME": first,
        "LASTNAME": last,
        "NPI": npi,
        "EXCLTYPE": "1128a1",
        "EXCLDATE": "20200101",
    }
    row.update(overrides)
    return row


def associate(name="Jordan Reyes", npi="1234567893"):
    return Associate(name=name, npi=npi)


def test_leie_verifier_matches_name_and_npi(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion()])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(), Credential())

    assert result.result == "excluded"
    assert result.details == {
        "matched_by": "name_and_npi",
        "exclusion_type": "1128a1",
        "exclusion_date": "20200101",
    }


def test_leie_verifier_normalizes_names_and_npi(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion(first="JORDAN", last="O'REYES", npi="123-456-7893")])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(name="Jordan O'Reyes"), Credential())

    assert result.result == "excluded"


def test_leie_verifier_does_not_exclude_different_npi_with_same_name(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion(npi="9876543210")])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(), Credential())

    assert result.result == "verified"
    assert result.details["source_status"] == "No exclusion found"


def test_leie_verifier_reports_npi_name_mismatch(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion(first="Casey", last="Nguyen")])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(), Credential())

    assert result.result == "mismatch"
    assert "NPI matches" in result.details["reason"]


@pytest.mark.parametrize("npi", [None, "", "0000000000"])
def test_leie_verifier_uses_name_when_npi_is_unavailable(tmp_path, monkeypatch, npi):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion(npi="0000000000")])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(npi=npi), Credential())

    assert result.result == "excluded"
    assert result.details["matched_by"] == "name_only"
    assert "match_warning" in result.details


def test_leie_verifier_returns_verified_for_nonmatching_name(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion()])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(
        associate(name="Casey Nguyen", npi="9876543210"), Credential()
    )

    assert result.result == "verified"


def test_leie_csv_is_loaded_once(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [exclusion()])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    first_read = leie.load_leie_records()
    csv_path.write_text("not the cached contents", encoding="utf-8")

    assert leie.load_leie_records() is first_read


def test_missing_leie_csv_returns_error(tmp_path, monkeypatch):
    csv_path = tmp_path / "missing.csv"
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(), Credential())

    assert result.result == "error"
    assert "Unable to load LEIE CSV" in result.details["reason"]


def test_leie_csv_with_missing_columns_returns_error(tmp_path, monkeypatch):
    csv_path = tmp_path / "UPDATED.csv"
    write_csv(csv_path, [], fields=["FIRSTNAME", "LASTNAME"])
    monkeypatch.setattr(leie, "LEIE_CSV_PATH", csv_path)

    result = leie.LeieVerifier().verify(associate(), Credential())

    assert result.result == "error"
    assert "missing required columns" in result.details["reason"]
