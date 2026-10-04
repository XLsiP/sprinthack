import os
import tempfile

# Point the app at a throwaway database before anything imports db.py.
os.environ["DATABASE_URL"] = "sqlite:///%s/test.db" % tempfile.mkdtemp()
os.environ["MOCK_DELAY_MS"] = "0"
os.environ["SCHEDULER_ENABLED"] = "0"  # no background thread during tests
os.environ.pop("HR_EMAIL", None)
os.environ.pop("ACCESS_PASSWORD", None)
os.environ.pop("ROSTER_FILE", None)
os.environ["SEED_SYNTHETIC"] = "1"  # tests use invented people, never the real roster
os.environ.pop("RENDER", None)
os.environ.pop("SEED_IF_EMPTY", None)
for _name in ("RESEND_API_KEY", "ALERT_EMAIL_OVERRIDE_TO", "ALERT_EMAIL_MAX_PER_RUN", "ALERT_EMAIL_FROM", "RESEND_API_URL"):
    os.environ.pop(_name, None)  # tests must never send real email


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def no_live_license_lookups(monkeypatch):
    """Tests must never query the real Michigan license site; a test that needs results patches `fetch`."""
    from verify import michigan_lara

    def refuse(*args, **kwargs):
        raise AssertionError("A test tried to run a live Michigan LARA lookup")

    monkeypatch.setattr(michigan_lara, "fetch", refuse)
    monkeypatch.setattr(michigan_lara, "MIN_INTERVAL_SECONDS", 0)


@pytest.fixture(autouse=True)
def no_live_board_lookups(monkeypatch):
    """Tests must never query the real ARDMS or NMTCB sites; a test that needs results patches `fetch`."""
    from verify import ardms, nmtcb_site

    def refuse(*args, **kwargs):
        raise AssertionError("A test tried to run a live ARDMS or NMTCB lookup")

    for module in (ardms, nmtcb_site):
        monkeypatch.setattr(module, "fetch", refuse)
        monkeypatch.setattr(module, "MIN_INTERVAL_SECONDS", 0)
