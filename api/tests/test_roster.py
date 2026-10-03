"""Roster import, using an invented fixture. Real staff names never appear in tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import roster
import scheduler
import seed
from db import Base, SessionLocal, engine
from main import app
from models import Associate, Credential, Verification

FIXTURE = Path(__file__).parent / "fixtures" / "roster.csv"


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    assert seed.seed(reset=True, roster_path=str(FIXTURE)) == 6
    with TestClient(app) as c:
        yield c


def people() -> dict[str, Associate]:
    with SessionLocal() as db:
        rows = db.scalars(select(Associate).options(
            selectinload(Associate.credentials).selectinload(Credential.credential_type),
            selectinload(Associate.credentials).selectinload(Credential.verifications),
        ))
        return {a.name: a for a in rows}


def test_people_are_merged_and_names_kept_as_written(client):
    loaded = people()
    assert sorted(loaded) == [
        "Avery Testperson", "Blake Testperson", "Casey Example-Hyphen", "Devon Fixture", "Emery Placeholder",
        "Finley Invented",
    ]
    assert {(a.facility, a.state, a.department, a.npi) for a in loaded.values()} == {
        ("Beacon Kalamazoo", "MI", "Imaging", None)
    }


def test_one_credential_per_list_with_nothing_invented(client):
    loaded = people()
    held = {name: sorted(c.credential_type.name for c in a.credentials) for name, a in loaded.items()}
    assert held["Avery Testperson"] == ["ARRT Registration", "Michigan License"]  # listed twice under ARRT
    assert held["Devon Fixture"] == ["ARDMS Registration"]
    assert held["Emery Placeholder"] == ["NMTCB Certification"]
    for associate in loaded.values():
        for c in associate.credentials:
            assert (c.number, c.issued_date, c.expires_date, c.verifications) == (None, None, None, [])
            assert c.status == "unverified"
            assert c.credential_type.verify_method == "manual"


def test_manager_spellings_collapse(client):
    emails = {a.manager_email for a in people().values()}
    assert emails == {"morgan.samplemgr@example.org", "riley.othermgr@example.org"}  # "Morgen" typo folded in
    assert roster.parse_manager("Samplemgr,Morgan E") == ("Morgan", "Samplemgr", True)
    assert roster.parse_manager("Othermgr, Riley") == ("Riley", "Othermgr", True)
    assert roster.parse_manager("Morgen Samplemgr") == ("Morgen", "Samplemgr", False)


def test_role_comes_from_the_first_list(client):
    loaded = people()
    assert loaded["Avery Testperson"].role == "Radiologic technologist (ARRT)"
    assert loaded["Finley Invented"].role == "Michigan-licensed staff"


def test_api_shows_unverified_and_the_largest_team(client):
    stats = client.get("/api/stats").json()
    assert stats["associates"] == 6 and stats["credentials"] == 7
    assert stats["by_status"]["unverified"] == 7 and stats["by_status"]["valid"] == 0
    assert stats["unverified"] == 7

    filters = client.get("/api/filters").json()
    assert filters["demo_manager"] == "morgan.samplemgr@example.org"
    assert filters["demo_team"] == "Imaging, Beacon Kalamazoo"
    assert len(client.get("/api/credentials", params={"status": "unverified"}).json()) == 7


def test_no_verifier_runs_on_roster_credentials(client, monkeypatch):
    monkeypatch.setenv("HR_EMAIL", "hr@example.org")
    credential_id = next(iter(people().values())).credentials[0].id

    refused = client.post("/api/verify/credential/%d" % credential_id)
    assert refused.status_code == 409 and "verified by hand" in refused.json()["detail"]

    associate_id = people()["Avery Testperson"].id
    assert client.post("/api/verify/associate/%d" % associate_id).json() == []
    assert client.post("/api/verify/all").json() == {"checked": 0, "by_result": {}, "skipped_manual": 7}

    run = scheduler.run_daily_job("manual")
    assert run.checked == 0 and run.alerts.sent == 0  # nothing verified, and no dates to alert on

    with SessionLocal() as db:
        assert db.scalars(select(Verification)).all() == []
        assert set(db.scalars(select(Credential.status))) == {"unverified"}


def test_bad_rosters_are_rejected(tmp_path):
    missing = tmp_path / "missing.csv"
    missing.write_text("first_name,last_name,manager\nA,B,C\n")
    with pytest.raises(ValueError, match="missing columns: source"):
        roster.read_rows(missing)

    unknown = tmp_path / "unknown.csv"
    unknown.write_text("first_name,last_name,manager,source\nA,B,C,SOMEWHERE\n")
    with pytest.raises(ValueError, match="line 2 has unknown source"):
        roster.read_rows(unknown)

    blank = tmp_path / "blank.csv"
    blank.write_text("first_name,last_name,manager,source\nA,,C,ARRT\n")
    with pytest.raises(ValueError, match="line 2 is missing a name"):
        roster.read_rows(blank)


def test_roster_file_env_is_used_on_startup(monkeypatch):
    Base.metadata.drop_all(engine)
    monkeypatch.delenv("SEED_SYNTHETIC")
    monkeypatch.setenv("SEED_IF_EMPTY", "1")
    monkeypatch.setenv("ROSTER_FILE", str(FIXTURE))
    with TestClient(app) as c:
        assert c.get("/api/stats").json()["associates"] == 6


def test_source_selection(monkeypatch, tmp_path):
    monkeypatch.delenv("SEED_SYNTHETIC")
    monkeypatch.delenv("ROSTER_FILE", raising=False)
    assert seed.choose_source() == (seed.DEFAULT_ROSTER, "built-in roster kzo.csv")
    assert seed.choose_source(synthetic=True)[0] is None
    assert seed.choose_source(roster_path=str(FIXTURE))[0] == FIXTURE

    monkeypatch.setenv("ROSTER_FILE", str(FIXTURE))
    assert seed.choose_source()[0] == FIXTURE
    monkeypatch.setenv("ROSTER_FILE", str(tmp_path / "missing.csv"))
    assert seed.choose_source()[0] == seed.DEFAULT_ROSTER  # a bad setting must not stop the app starting

    monkeypatch.setenv("SEED_SYNTHETIC", "1")
    assert seed.choose_source()[0] is None
    assert seed.choose_source(roster_path=str(FIXTURE))[0] == FIXTURE  # an explicit file still wins
    with pytest.raises(SystemExit, match="Roster file not found"):
        seed.choose_source(roster_path=str(tmp_path / "missing.csv"))


def test_built_in_roster_loads(monkeypatch):
    """Counts only: this test must never name the real people in the roster."""
    monkeypatch.delenv("SEED_SYNTHETIC")
    assert seed.seed(reset=True) == 151
    assert seed.last_source == "built-in roster kzo.csv"
    with SessionLocal() as db:
        associates = db.scalars(select(Associate)).all()
        credentials = db.scalars(select(Credential)).all()
        assert len({a.manager_email for a in associates}) == 5
        assert len(credentials) == 151 and {c.status for c in credentials} == {"unverified"}
        assert all(c.number is None and c.expires_date is None for c in credentials)
        assert db.scalars(select(Verification)).all() == []
