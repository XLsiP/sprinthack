"""The ARDMS and NMTCB lookups, and "Verify all" running them on request.

Invented pages shaped like the real ones. No live calls, no real names.
"""
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import scheduler
import seed
from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, Verification
from verify import ardms, michigan_lara, nmtcb_site

FIXTURE = Path(__file__).parent / "fixtures" / "roster.csv"


def ardms_page(*people):
    """Each person is (name, [(credential, specialty, valid from, valid until, status), ...])."""
    panels = "".join(
        '<div class="panel-item"><h6>%s <span class="normal">United States</span></h6>'
        "<table class=\"sv-listing-table\"><thead><tr><th>Credential:</th><th>Specialty:</th><th>Valid from:</th>"
        "<th>Valid until:</th><th>Status</th></tr></thead><tbody>%s</tbody></table></div>"
        % (name, "".join("<tr>%s</tr>" % "".join("<td> %s </td>" % cell for cell in row) for row in rows))
        for name, rows in people
    )
    return '<html><div class="panel-listing" id="status-verif-listing">%s</div></html>' % (panels or "No results found, try refining your search above.")


RDMS = "Registered Diagnostic Medical Sonographer"


def nmtcb_results(*people):
    links = "".join('<li><a href="/verification/%d">%s</a> - Sampletown, MI</li>' % (i, name) for i, name in people)
    body = "<ul>%s</ul>" % links if people else "<div>Sorry, but we cannot find an entry to match your query.</div>"
    return '<section class="content-section" id="main-section">%s</section>' % body


def nmtcb_person(name="Emery Placeholder", status="ACTIVE", through="2099-07-31"):
    block = '<div class="details-block"><h6>%s</h6><div class="details-value">%s</div></div>'
    return '<section id="main-section"><div class="details-card">%s</div><em>attests to the accuracy of this certification information as of: 10/01/2026</em></section>' % "".join((
        block % ("NAME", name), block % ("Address", "<address>Sampletown, MI</address>"),
        block % ("Certifications Held", "<p>CNMT</p>"),
        block % ("Current Status", "<dl><dt>CNMT:</dt><dd>%s</dd></dl>" % status),
        block % ("Certified Through", '<dl><dt>CNMT:</dt><dd><time datetime="%s">07/31/2099</time></dd></dl>' % through),
    ))


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    seed.seed(reset=True, roster_path=str(FIXTURE))
    with TestClient(app) as c:
        yield c


def credential(source: str) -> Credential:
    with SessionLocal() as db:
        return db.scalar(select(Credential).where(Credential.credential_type.has(issuing_source=source)))


def answers(monkeypatch, ardms_answer=None, results=None, person=None, michigan=None):
    """Stand in for the three sites; an exception as an answer is raised."""
    def give(value):
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(ardms, "fetch", lambda name: give(ardms_page() if ardms_answer is None else ardms_answer))
    monkeypatch.setattr(nmtcb_site, "fetch", lambda url, params=None: give(
        (nmtcb_results() if results is None else results) if params else (person or nmtcb_person())
    ))
    monkeypatch.setattr(michigan_lara, "fetch", lambda first="", last="", number="": give(
        michigan or (michigan_lara.URL, "Your search returned no results")
    ))


def latest(source: str) -> Verification:
    with SessionLocal() as db:
        return db.scalars(select(Verification).where(Verification.source == source).order_by(Verification.id.desc())).first()


def test_parsers():
    people = ardms.parse(ardms_page(("DEVON FIXTURE", [(RDMS, "AB", "July 18 2007", "December 31 2099", "Active")])))
    assert people == [{"name": "DEVON FIXTURE", "country": "United States", "credentials": [{
        "credential": RDMS, "specialty": "AB", "valid_from": "July 18 2007", "valid_until": "December 31 2099", "status": "Active",
    }]}]
    assert ardms.parse(ardms_page()) == []
    with pytest.raises(ValueError):
        ardms.parse("<html>Service unavailable</html>")

    assert nmtcb_site.parse_results(nmtcb_results((7, "Emery Q Placeholder"))) == [{"path": "/verification/7", "name": "Emery Q Placeholder"}]
    assert nmtcb_site.parse_results(nmtcb_results()) == []
    person = nmtcb_site.parse_person(nmtcb_person())
    assert (person["name"], person["statuses"], person["dates"], person["as_of"]) == ("Emery Placeholder", ["ACTIVE"], ["2099-07-31"], "10/01/2026")
    with pytest.raises(ValueError):
        nmtcb_site.parse_results("<html>Service unavailable</html>")


def test_verify_all_fills_in_what_the_three_sources_show(client, monkeypatch):
    answers(
        monkeypatch,
        ardms_answer=ardms_page(("DEVON FIXTURE", [
            (RDMS, "AB", "July 18 2007", "December 31 2099", "Active"), (RDMS, "OBGYN", "May 2 2010", "December 31 2098", "Active"),
        ])),
        results=nmtcb_results((7, "Emery Placeholder")),
    )
    summary = client.post("/api/verify/all").json()
    # ARDMS and NMTCB verified, the two Michigan names not found (left for a person), three ARRT skipped.
    assert summary == {"checked": 4, "by_result": {"verified": 2, "error": 2}, "skipped_manual": 3}

    found = credential("ARDMS")
    assert (found.status, found.issued_date.isoformat(), found.expires_date.isoformat(), found.number) == (
        "valid", "2007-07-18", "2098-12-31", None,  # the credential that runs out first
    )
    details = latest("ARDMS").details
    assert details["credentials_held"] == RDMS + " (AB, OBGYN)" and details["source_status"] == "Active"
    assert details["1. %s, AB" % RDMS] == "valid from July 18 2007, until December 31 2099, Active"
    assert "entered_by_hand" not in details

    found = credential("NMTCB")
    assert (found.status, found.expires_date.isoformat()) == ("valid", "2099-07-31")
    details = latest("NMTCB").details
    assert (details["credentials_held"], details["source_status"], details["Location"]) == ("CNMT", "CNMT: ACTIVE", "Sampletown, MI")
    assert details["lookup_url"] == "https://www.nmtcb.org/verification/7"

    assert credential("Michigan LARA").status == "unverified" and latest("Michigan LARA").details["needs_review"] is True
    assert credential("ARRT").status == "unverified" and latest("ARRT") is None


def test_nobody_is_picked_when_several_people_match(client, monkeypatch):
    row = [(RDMS, "AB", "July 18 2007", "December 31 2099", "Active")]
    answers(
        monkeypatch, ardms_answer=ardms_page(("DEVON FIXTURE", row), ("DEVON A FIXTURE", row)),
        results=nmtcb_results((7, "Emery Placeholder"), (8, "Emery B Placeholder")),
    )
    assert client.post("/api/verify/all").json()["by_result"] == {"error": 4}
    for source in ("ARDMS", "NMTCB"):
        details = latest(source).details
        assert details["needs_review"] is True and "2 people match this name" in details["reason"]
        assert (credential(source).status, credential(source).expires_date) == ("unverified", None)


def test_no_match_and_a_wrong_name_are_left_for_a_person(client, monkeypatch):
    answers(monkeypatch, ardms_answer=ardms_page(("SOMEONE ELSE", [(RDMS, "AB", "July 18 2007", "December 31 2099", "Active")])))
    client.post("/api/verify/all")
    assert "did not clearly match" in latest("ARDMS").details["reason"]
    assert "may be listed under another name" in latest("NMTCB").details["reason"] and latest("NMTCB").result == "error"
    assert {credential(source).status for source in ("ARDMS", "NMTCB")} == {"unverified"}


def test_inactive_is_a_mismatch(client, monkeypatch):
    answers(
        monkeypatch, ardms_answer=ardms_page(("DEVON FIXTURE", [(RDMS, "AB", "July 18 2007", "December 31 2020", "Expired")])),
        results=nmtcb_results((7, "Emery Placeholder")), person=nmtcb_person(status="INACTIVE"),
    )
    assert client.post("/api/verify/all").json()["by_result"] == {"mismatch": 2, "error": 2}
    assert latest("ARDMS").details["reason"] == "Status is Expired" and latest("NMTCB").details["reason"] == "Status is CNMT: INACTIVE"
    assert {credential(source).status for source in ("ARDMS", "NMTCB")} == {"expired", "verification_failed"}


@pytest.mark.parametrize("failure", [httpx.ConnectError("down"), "<html>Service unavailable</html>"])
def test_site_problems_leave_the_credential_alone(client, monkeypatch, failure):
    answers(monkeypatch, ardms_answer=failure, results=failure)
    assert client.post("/api/verify/all").json()["by_result"] == {"error": 4}
    for source in ("ARDMS", "NMTCB"):
        assert latest(source).details["reason"].startswith("Could not check") and "needs_review" not in latest(source).details
        assert credential(source).status == "unverified"


def test_a_managers_verify_all_only_touches_their_team(client, monkeypatch):
    answers(monkeypatch, ardms_answer=ardms_page(("DEVON FIXTURE", [(RDMS, "AB", "July 18 2007", "December 31 2099", "Active")])),
            results=nmtcb_results((7, "Emery Placeholder")))
    summary = client.post("/api/verify/all", params={"manager": "riley.othermgr@example.org"}).json()
    assert summary == {"checked": 1, "by_result": {"verified": 1}, "skipped_manual": 1}  # NMTCB checked, one ARRT skipped
    with SessionLocal() as db:
        assert {v.source for v in db.scalars(select(Verification))} == {"NMTCB"}
    assert credential("ARDMS").status == "unverified"  # the other manager's person was not looked up


def test_only_verify_all_runs_them_and_hand_entry_still_works(client):
    """No `answers` here: the autouse guards fail the test if anything tries a live lookup."""
    with SessionLocal() as db:
        associate_id = db.scalar(select(Associate.id).where(Associate.name == "Devon Fixture"))
    cid = credential("ARDMS").id
    assert client.post("/api/verify/credential/%d" % cid).status_code == 409
    assert client.post("/api/verify/associate/%d" % associate_id).json() == []
    assert scheduler.run_daily_job("manual").checked == 0
    assert latest("ARDMS") is None

    saved = client.post("/api/verify/credential/%d/manual" % cid, json={"result": "verified", "expires_date": "2099-12-31"})
    assert saved.status_code == 200 and credential("ARDMS").status == "valid"
