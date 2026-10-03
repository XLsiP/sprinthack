"""Load fake demo data. Dates are relative to today so the dashboard always shows a mix.

Usage: python seed.py
"""
from datetime import date, timedelta

from app import db

STAFF = [
    # name, role, email, manager_email, [(type, number, state, days until expiry)]
    ("Jordan Reyes", "RN", "jordan@example.com", "manager@example.com",
     [("RN License", "RN123456", "CA", 12), ("BLS", None, None, 200)]),
    ("Sam Patel", "MD", "sam@example.com", "manager@example.com",
     [("Medical License", "A98765", "CA", 75), ("DEA", "BP1234563", None, -5), ("ACLS", None, None, 400)]),
    ("Casey Nguyen", "PA", "casey@example.com", "hr@example.com",
     [("PA License", "PA55521", "NY", 310), ("BLS", None, None, 28)]),
]


def main():
    db.init_db()
    today = date.today()
    with db.connect() as conn:
        conn.execute("DELETE FROM staff")
        for name, role, email, manager_email, creds in STAFF:
            staff_id = conn.execute(
                "INSERT INTO staff (name, role, email, manager_email) VALUES (?, ?, ?, ?)",
                (name, role, email, manager_email),
            ).lastrowid
            for ctype, number, state, days in creds:
                conn.execute(
                    "INSERT INTO credentials (staff_id, type, number, state, expires_on) VALUES (?, ?, ?, ?, ?)",
                    (staff_id, ctype, number, state, (today + timedelta(days=days)).isoformat()),
                )
    print("Seeded %d staff." % len(STAFF))


if __name__ == "__main__":
    main()
