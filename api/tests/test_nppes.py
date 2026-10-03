import httpx
import pytest

from models import Associate, Credential
from verify.nppes import NppesVerifier, lookup_npi, match_name, match_taxonomy


def make_associate(name="Jordan Reyes", role="Radiologic Technologist", npi="1234567893"):
    associate = Associate(name=name, role=role)
    associate.npi = npi
    return associate


def make_credential(number=None):
    return Credential(number=number)


def provider(
    first_name="Jordan",
    last_name="Reyes",
    status="A",
    taxonomies=None,
):
    return {
        "basic": {"first_name": first_name, "last_name": last_name, "status": status},
        "taxonomies": taxonomies if taxonomies is not None else [{"desc": "Radiologic Technologist"}],
    }


def test_lookup_npi_uses_api_version_and_returns_first_match(monkeypatch):
    response = httpx.Response(
        200,
        json={"results": [{"number": "1234567893"}, {"number": "1234567894"}]},
        request=httpx.Request("GET", "https://npiregistry.cms.hhs.gov/api/"),
    )
    requests = []

    def get(url, **kwargs):
        requests.append((url, kwargs))
        return response

    monkeypatch.setattr("verify.nppes.httpx.get", get)

    assert lookup_npi("1234567893") == {"number": "1234567893"}
    assert requests[0][1]["params"] == {"version": "2.1", "number": "1234567893"}
    assert requests[0][1]["timeout"] == 10


def test_lookup_npi_returns_none_when_registry_has_no_results(monkeypatch):
    response = httpx.Response(
        200,
        json={"results": []},
        request=httpx.Request("GET", "https://npiregistry.cms.hhs.gov/api/"),
    )
    monkeypatch.setattr("verify.nppes.httpx.get", lambda *args, **kwargs: response)

    assert lookup_npi("1234567893") is None


def test_match_name_ignores_case_punctuation_and_middle_name():
    assert match_name(
        "jordan m. reyes",
        {"basic": {"first_name": "Jordan", "last_name": "Reyes"}},
    )
    assert not match_name(
        "Jordan Reyes",
        {"basic": {"first_name": "Jordan", "last_name": "Smith"}},
    )


@pytest.mark.parametrize(
    ("role", "description"),
    [
        ("Radiologist", "Diagnostic Radiology"),
        ("CT Technologist", "Radiologic Technologist"),
        ("Registered Nurse", "Registered Nurse"),
    ],
)
def test_match_taxonomy_supports_role_categories(role, description):
    assert match_taxonomy(role, {"taxonomies": [{"desc": description}]})


def test_match_taxonomy_rejects_unrelated_and_missing_taxonomy():
    assert not match_taxonomy(
        "Radiologic Technologist", {"taxonomies": [{"desc": "Registered Nurse"}]}
    )
    assert not match_taxonomy("Radiologic Technologist", {"taxonomies": []})


def test_verifier_returns_verified_for_matching_active_record(monkeypatch):
    monkeypatch.setattr("verify.nppes.lookup_npi", lambda npi: provider())

    result = NppesVerifier().verify(make_associate(), make_credential())

    assert result.result == "verified"
    assert result.details["name_matches"] is True
    assert result.details["taxonomy_matches_role"] is True


@pytest.mark.parametrize(
    ("registry_record", "reason"),
    [
        (provider(first_name="Casey"), "Registry name does not match"),
        (
            provider(taxonomies=[{"desc": "Registered Nurse"}]),
            "Registry taxonomy does not match",
        ),
    ],
)
def test_verifier_returns_mismatch_for_name_or_taxonomy(registry_record, reason, monkeypatch):
    monkeypatch.setattr("verify.nppes.lookup_npi", lambda npi: registry_record)

    result = NppesVerifier().verify(make_associate(), make_credential())

    assert result.result == "mismatch"
    assert reason in result.details["reason"]


def test_verifier_returns_not_found_without_valid_npi_or_registry_record(monkeypatch):
    verifier = NppesVerifier()
    monkeypatch.setattr("verify.nppes.lookup_npi", lambda npi: None)

    assert verifier.verify(make_associate(npi=None), make_credential()).result == "not_found"
    assert verifier.verify(make_associate(npi="1234567890"), make_credential()).result == "not_found"
    assert verifier.verify(make_associate(), make_credential()).result == "not_found"


def test_verifier_converts_registry_timeout_to_error(monkeypatch):
    def raise_timeout(npi):
        raise httpx.TimeoutException("registry timed out")

    monkeypatch.setattr("verify.nppes.lookup_npi", raise_timeout)

    result = NppesVerifier().verify(make_associate(), make_credential())

    assert result.result == "error"
    assert result.details["reason"] == "registry timed out"
