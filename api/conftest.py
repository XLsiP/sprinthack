import os
import tempfile

# Point the app at a throwaway database before anything imports db.py.
os.environ["DATABASE_URL"] = "sqlite:///%s/test.db" % tempfile.mkdtemp()
os.environ["MOCK_DELAY_MS"] = "0"
