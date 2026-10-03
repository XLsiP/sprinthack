import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "credentials.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS staff (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL,
    npi           TEXT,
    email         TEXT,
    manager_email TEXT
);

CREATE TABLE IF NOT EXISTS credentials (
    id                  INTEGER PRIMARY KEY,
    staff_id            INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    type                TEXT NOT NULL,      -- e.g. "RN License", "DEA", "BLS", "ACLS"
    number              TEXT,
    state               TEXT,               -- two-letter state, if applicable
    expires_on          TEXT NOT NULL,      -- ISO date
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    verification_source TEXT,
    verified_at         TEXT
);
"""


def connect():
    conn = sqlite3.connect(os.environ.get("CRED_DB", str(DEFAULT_DB)))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
