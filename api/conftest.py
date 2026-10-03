import os
import tempfile

# Point the app at a throwaway database before anything imports db.py.
os.environ["DATABASE_URL"] = "sqlite:///%s/test.db" % tempfile.mkdtemp()
os.environ["MOCK_DELAY_MS"] = "0"
os.environ["SCHEDULER_ENABLED"] = "0"  # no background thread during tests
os.environ.pop("HR_EMAIL", None)
os.environ.pop("ROSTER_FILE", None)
os.environ.pop("RENDER", None)
os.environ.pop("SEED_IF_EMPTY", None)
for _name in ("RESEND_API_KEY", "ALERT_EMAIL_OVERRIDE_TO", "ALERT_EMAIL_MAX_PER_RUN", "ALERT_EMAIL_FROM", "RESEND_API_URL"):
    os.environ.pop(_name, None)  # tests must never send real email
