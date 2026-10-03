import os
import tempfile

# Point the app at a throwaway database before anything imports db.py.
os.environ["DATABASE_URL"] = "sqlite:///%s/test.db" % tempfile.mkdtemp()
os.environ["MOCK_DELAY_MS"] = "0"
os.environ["SCHEDULER_ENABLED"] = "0"  # no background thread during tests
os.environ.pop("HR_EMAIL", None)
