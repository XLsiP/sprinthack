"""Michigan LARA verifier, against invented pages shaped like the real ones. No live calls, no real names."""
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import seed
from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, Verification
from verify import michigan_lara

FIXTURE = Path(__file__).parent / "fixtures" / "roster.csv"
DETAIL_URL = "https://aca-prod.accela.com/MILARA/GeneralProperty/LicenseeDetail.aspx?LicenseeNumber=4700000001"


def detail_page(number="4700000001", name="Finley Q Invented", status="Active", expires="03/04/2099"):
    return (
        "<html><body><span>License Number: </span><span>%s</span><span>Name: </span><span>%s</span>"
        "<span>License Issue Date: </span><span>01/02/2020</span><span>License Expiration Date: </span>"
        "<span>%s</span><span>License Status: </span><span>%s</span><span>County: </span><span>Kalamazoo</span>"
        "<h1>Related Records</h1><p>Listed below are the records associated with Registered Nurse, "
        "License Number: %s</p><script>var x = 'License Number: 999';</script></body></html>"
    ) % (number, name, expires, status, number)


def list_page(*rows):
    cells = "".join(
        '<tr class="ACA_TabRow_Odd ACA_TabRow_Odd_FontSize">'
        + "".join("<td><span>%s</span></td>" % value for value in row) + "</tr>"
        for row in rows
    )
    return "<html><body><table><tr><th>License Type</th></tr>%s</table></body></html>" % cells


def row(license_type, number, first, middle, last, status, expires):
    return (license_type, number, first, middle, last, "", "", status, expires)


NONE_PAGE = "<html><body>Notice: Your search returned no results. Please modify your search criteria.</body></html>"
SEARCH_URL = michigan_lara.URL


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    assert seed.seed(reset=True, roster_path=str(FIXTURE)) == 6
    with TestClient(app) as c:
        yield c


def michigan_credential(name="Finley Invented") -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(Credential.id).join(Associate).where(Associate.name == name).join(Credential.credential_type)
            .where(Credential.credential_type.has(name="Michigan License"))
        )


def answer(monkeypatch, url, page):
    calls = []

    def fetch(first="", last="", number=""):
        calls.append({"first": first, "last": last, "number": number})
        if isinstance(page, Exception):
            raise page
        return url, page

    monkeypatch.setattr(michigan_lara, "fetch", fetch)
    return calls


def test_parsers():
    record = michigan_lara.parse_detail(detail_page())
    assert record == {
        "license_type": "Registered Nurse", "license_number": "4700000001", "name": "Finley Q Invented",
        "status": "Active", "issued_date": "2020-01-02", "expires_date": "2099-03-04", "county": "Kalamazoo",
    }
    records = michigan_lara.parse_list(list_page(
        row("Licensed Practical Nurse", "4700000002", "Finley", "Q", "Invented", "Lapsed", "03/31/2008"),
        row("Registered Nurse", "4700000001", "Finley", "Q", "Invented", "Active", "03/04/2099"),
    ))
    assert [r["license_number"] for r in records] == ["4700000002", "4700000001"]
    assert records[0]["name"] == "Finley Q Invented" and records[0]["expires_date"] == "2008-03-31"
    assert michigan_lara.no_results(NONE_PAGE) and not michigan_lara.no_results(detail_page())
    assert michigan_lara.parse_detail(NONE_PAGE) is None and michigan_lara.parse_list(NONE_PAGE) == []
    assert michigan_lara.split_name("Mary Beth Example") == ("Mary Beth", "Example")
    assert michigan_lara.hidden_fields('<input type="hidden" name="ACA_CS_FIELD" value="a&amp;b" />') == {
        "ACA_CS_FIELD": "a&b"
    }


def test_single_match_fills_in_the_credential(client, monkeypatch):
    calls = answer(monkeypatch, DETAIL_URL, detail_page())
    credential_id = michigan_credential()

    result = client.post("/api/verify/credential/%d" % credential_id).json()

    assert calls == [{"first": "Finley", "last": "Invented", "number": ""}]
    assert result["result"] == "verified" and result["source"] == "Michigan LARA"
    assert result["details"]["license_number"] == "4700000001" and result["details"]["status"] == "Active"
    with SessionLocal() as db:
        credential = db.get(Credential, credential_id)
        assert credential.number == "4700000001"
        assert (credential.issued_date, credential.expires_date) == (date(2020, 1, 2), date(2099, 3, 4))
        assert credential.status == "valid"


def test_recheck_searches_by_license_number(client, monkeypatch):
    credential_id = michigan_credential()
    answer(monkeypatch, DETAIL_URL, detail_page())
    client.post("/api/verify/credential/%d" % credential_id)

    calls = answer(monkeypatch, DETAIL_URL, detail_page(expires="03/04/2101"))
    client.post("/api/verify/credential/%d" % credential_id)

    assert calls == [{"first": "", "last": "", "number": "4700000001"}]
    with SessionLocal() as db:
        assert db.get(Credential, credential_id).expires_date == date(2101, 3, 4)


def test_no_match(client, monkeypatch):
    answer(monkeypatch, SEARCH_URL, NONE_PAGE)
    credential_id = michigan_credential()
    result = client.post("/api/verify/credential/%d" % credential_id).json()
    assert result["result"] == "not_found" and "No Michigan license found under this name" in result["details"]["reason"]
    with SessionLocal() as db:
        credential = db.get(Credential, credential_id)
        assert credential.status == "verification_failed" and credential.number is None


def test_same_person_with_an_old_license_uses_the_current_one(client, monkeypatch):
    answer(monkeypatch, SEARCH_URL, list_page(
        row("Licensed Practical Nurse", "4700000002", "Finley", "Q", "Invented", "Lapsed", "03/31/2008"),
        row("Registered Nurse", "4700000001", "Finley", "Q", "Invented", "Active", "03/04/2099"),
    ))
    credential_id = michigan_credential()
    result = client.post("/api/verify/credential/%d" % credential_id).json()
    assert result["result"] == "verified" and result["details"]["license_number"] == "4700000001"
    assert [r["license_number"] for r in result["details"]["other_licenses"]] == ["4700000002"]


def test_different_people_with_one_name_are_not_guessed(client, monkeypatch):
    answer(monkeypatch, SEARCH_URL, list_page(
        row("Registered Nurse", "4700000001", "Finley", "Q", "Invented", "Active", "03/04/2099"),
        row("Registered Nurse", "4700000003", "Finley", "Z", "Invented", "Active", "05/06/2098"),
    ))
    credential_id = michigan_credential()
    result = client.post("/api/verify/credential/%d" % credential_id).json()
    assert result["result"] == "error" and result["details"]["needs_review"] is True
    assert "2 different people match this name" in result["details"]["reason"]
    assert len(result["details"]["candidates"]) == 2
    with SessionLocal() as db:
        credential = db.get(Credential, credential_id)
        assert credential.status == "unverified" and credential.number is None and credential.expires_date is None


def test_inactive_license_is_a_mismatch(client, monkeypatch):
    answer(monkeypatch, DETAIL_URL, detail_page(status="Lapsed", expires="03/04/2099"))
    credential_id = michigan_credential()
    result = client.post("/api/verify/credential/%d" % credential_id).json()
    assert result["result"] == "mismatch" and result["details"]["reason"] == "License status is Lapsed"
    with SessionLocal() as db:
        assert db.get(Credential, credential_id).status == "verification_failed"


@pytest.mark.parametrize("failure", [
    httpx.ConnectTimeout("timed out"),
    ValueError("The Michigan lookup page rejected the search"),
])
def test_site_problems_leave_the_credential_alone(client, monkeypatch, failure):
    answer(monkeypatch, SEARCH_URL, failure)
    credential_id = michigan_credential()
    result = client.post("/api/verify/credential/%d" % credential_id).json()
    assert result["result"] == "error" and result["details"]["reason"].startswith("Could not check")
    with SessionLocal() as db:
        assert db.get(Credential, credential_id).status == "unverified"


def test_unreadable_page_is_an_error(monkeypatch):
    answer(monkeypatch, SEARCH_URL, "<html><body>Something unexpected</body></html>")
    with pytest.raises(ValueError, match="could not be read"):
        michigan_lara.lookup(first="Finley", last="Invented")
    answer(monkeypatch, "https://aca-prod.accela.com/MILARA/Error.aspx?ErrorId=1", "<html></html>")
    with pytest.raises(ValueError, match="rejected the search"):
        michigan_lara.lookup(first="Finley", last="Invented")


def test_verify_all_checks_michigan_and_skips_hand_verified(client, monkeypatch):
    calls = answer(monkeypatch, DETAIL_URL, detail_page())
    summary = client.post("/api/verify/all").json()
    assert summary == {"checked": 2, "by_result": {"verified": 2}, "skipped_manual": 5}
    assert len(calls) == 2
    with SessionLocal() as db:
        assert {v.source for v in db.scalars(select(Verification))} == {"Michigan LARA"}


def test_synthetic_michigan_licenses_still_use_the_mock(monkeypatch):
    """Invented people must never be looked up on the real state site."""
    Base.metadata.drop_all(engine)
    seed.seed(reset=True, synthetic=True)
    with SessionLocal() as db:
        credential_id = db.scalar(
            select(Credential.id).where(Credential.credential_type.has(name="Michigan State License")).limit(1)
        )
    with TestClient(app) as c:  # the autouse guard fails the test if `fetch` is called
        result = c.post("/api/verify/credential/%d" % credential_id).json()
    assert result["details"]["mock"] is True
