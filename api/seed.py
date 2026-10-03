"""Synthetic data generator. Every name, NPI and credential number here is invented.

Usage: python seed.py --reset
Dates are relative to today so the dashboard always shows a mix of statuses.
"""
import argparse
import random
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select

from db import Base, SessionLocal, engine
from models import Associate, Credential, CredentialType, RoleRequirement, Verification
from status import refresh_statuses
from verify.mock import mock_outcome
from verify.nppes import npi_checksum_ok

TOTAL_ASSOCIATES = 1500
RADIOLOGY_TEAM = 60
DEMO_FACILITY = "Memorial Hospital of South Bend"
DEMO_MANAGER = "radiology.manager@example.org"

# Beacon's 11 hospitals (name, state), from the system's public fact sheet.
FACILITIES = [
    ("Memorial Hospital of South Bend", "IN"), ("Beacon Children's Hospital", "IN"), ("Epworth Hospital", "IN"),
    ("Elkhart General Hospital", "IN"), ("Community Hospital of Bremen", "IN"), ("Beacon Granger Hospital", "IN"),
    ("Three Rivers Hospital", "MI"), ("Beacon Kalamazoo", "MI"), ("Beacon Allegan", "MI"),
    ("Beacon Plainwell", "MI"), ("Beacon Dowagiac", "MI"),
]

# name, issuing_source (must match a verifier's `source`), verify_method, renewal_months, number prefix
TYPES = [
    ("Indiana State License", "Indiana PLA", "mock", 24, "IN"),
    ("Michigan State License", "Michigan LARA", "mock", 24, "MI"),
    ("ARRT RT(R)", "ARRT", "mock", 12, "RTR"),
    ("ARRT CT", "ARRT", "mock", 12, "CT"),
    ("NMTCB Certification", "NMTCB", "mock", 12, "NMT"),
    ("BLS", "American Heart Association", "mock", 24, "BLS"),
    ("NPI Registration", "NPPES", "api", None, ""),
    ("OIG Exclusion Check", "OIG LEIE", "file", None, ""),
]
STATE_LICENSE = {"IN": "Indiana State License", "MI": "Michigan State License"}

# Requirements besides the state license (which follows the associate's work state).
ROLES = {
    "Radiologic Technologist": ["ARRT RT(R)", "BLS", "OIG Exclusion Check"],
    "CT Technologist": ["ARRT RT(R)", "ARRT CT", "BLS", "OIG Exclusion Check"],
    "MRI Technologist": ["ARRT RT(R)", "BLS", "OIG Exclusion Check"],
    "Nuclear Medicine Technologist": ["NMTCB Certification", "BLS", "OIG Exclusion Check"],
    "Radiologist": ["NPI Registration", "BLS", "OIG Exclusion Check"],
    "Registered Nurse": ["BLS", "OIG Exclusion Check"],
    "Nurse Practitioner": ["NPI Registration", "BLS", "OIG Exclusion Check"],
    "Physician": ["NPI Registration", "BLS", "OIG Exclusion Check"],
    "Respiratory Therapist": ["BLS", "OIG Exclusion Check"],
    "Pharmacist": ["NPI Registration", "OIG Exclusion Check"],
}
RADIOLOGY_ROLES = [
    ("Radiologic Technologist", 26), ("CT Technologist", 12), ("MRI Technologist", 9),
    ("Nuclear Medicine Technologist", 7), ("Radiologist", 6),
]
DEPARTMENTS = {
    "Radiology": [r for r, _ in RADIOLOGY_ROLES],
    "Emergency": ["Registered Nurse", "Physician", "Nurse Practitioner", "Respiratory Therapist"],
    "Surgery": ["Registered Nurse", "Physician"],
    "Cardiology": ["Registered Nurse", "Physician", "Nurse Practitioner"],
    "Intensive Care": ["Registered Nurse", "Physician", "Respiratory Therapist"],
    "Pharmacy": ["Pharmacist"],
    "Pediatrics": ["Registered Nurse", "Physician", "Nurse Practitioner"],
}

FIRST = """Avery Blake Cameron Dakota Emerson Finley Harper Jordan Kendall Logan Morgan Parker Quinn Reese Riley
Rowan Sawyer Skyler Taylor Tatum Alex Casey Devon Elliot Frankie Hayden Jamie Kai Lane Marlow Noel Oakley Peyton
Remy Sage Shiloh Toby Val Wren Arden""".split()
LAST = """Abbott Barlow Calloway Dunmore Ellery Fairbanks Garrick Hollis Iverson Jessup Kimball Lachance Merrow
Northcott Oakhurst Pemberton Quimby Radcliff Stanhope Thackeray Underhill Vance Whitlock Yarrow Zeller Ashdown
Birchall Coldwell Draycott Everhart Fenwick Greaves Hartwell Inglis Kettering Lockridge Marwood Netherby Orchard
Pinecrest""".split()

# Days until expiry, weighted: mostly valid, a tail of expiring and expired.
EXPIRY_BUCKETS = [((91, 700), 82), ((61, 90), 7), ((31, 60), 5), ((1, 30), 4), ((-60, -1), 2)]


def fake_npi(rng: random.Random) -> str:
    """A 10-digit number that fails the NPI checksum, so it can never be a real provider's NPI."""
    while True:
        npi = "1" + "".join(rng.choice("0123456789") for _ in range(9))
        if not npi_checksum_ok(npi):
            return npi


def days_until_expiry(rng: random.Random) -> int:
    (low, high), = rng.choices([b for b, _ in EXPIRY_BUCKETS], weights=[w for _, w in EXPIRY_BUCKETS])
    return rng.randint(low, high)


def seed(reset: bool, today: Optional[date] = None) -> int:
    rng = random.Random(42)
    today = today or date.today()
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        if db.scalar(select(func.count(Associate.id))):
            raise SystemExit("Database already has data. Run: python seed.py --reset")

        types = {}
        prefixes = {}
        for name, source, method, months, prefix in TYPES:
            types[name] = CredentialType(name=name, issuing_source=source, verify_method=method, renewal_months=months)
            prefixes[name] = prefix
        db.add_all(types.values())
        db.flush()
        for role, required in ROLES.items():
            for name in list(STATE_LICENSE.values()) + required:
                db.add(RoleRequirement(role=role, credential_type_id=types[name].id))

        def add_associate(role: str, department: str, facility: str, state: str, manager: str,
                          expiry_days: Optional[int] = None, verified: Optional[bool] = None) -> Associate:
            needs_npi = "NPI Registration" in ROLES[role]
            associate = Associate(
                name="%s %s" % (rng.choice(FIRST), rng.choice(LAST)), npi=fake_npi(rng) if needs_npi else None,
                role=role, department=department, facility=facility, state=state, manager_email=manager,
            )
            licenses = [STATE_LICENSE[state]]
            if rng.random() < 0.06:  # works across the state line; no reciprocity, so both licenses
                licenses.append(STATE_LICENSE["MI" if state == "IN" else "IN"])
            for i, type_name in enumerate(licenses + ROLES[role]):
                ctype = types[type_name]
                credential = Credential(credential_type=ctype)
                if ctype.renewal_months:
                    # `expiry_days` pins the associate's first credential; the rest stay healthy.
                    days = expiry_days if (expiry_days is not None and i == 0) else (
                        rng.randint(120, 700) if expiry_days is not None else days_until_expiry(rng))
                    credential.expires_date = today + timedelta(days=days)
                    credential.issued_date = credential.expires_date - timedelta(days=ctype.renewal_months * 30)
                    credential.number = "%s-%07d" % (prefixes[type_name], rng.randint(0, 9_999_999))
                elif type_name == "NPI Registration":
                    credential.number = associate.npi
                # NPI rows start unverified: seed NPIs are fake, so there is nothing real to have checked.
                was_verified = verified if verified is not None else rng.random() < 0.85
                if was_verified and type_name != "NPI Registration":
                    result = mock_outcome(credential.number) if credential.number else "verified"
                    credential.verifications.append(Verification(
                        checked_at=datetime.combine(today - timedelta(days=rng.randint(1, 120)), datetime.min.time()),
                        source=ctype.issuing_source, result=result, details={"mock": True, "seeded": True},
                    ))
                associate.credentials.append(credential)
            db.add(associate)
            return associate

        # The demo manager's 60-person radiology team, with a guaranteed mix.
        pinned = [-45, -12, -3, 4, 11, 19, 27, 38, 52, 59, 66, 74, 88] + [None] * RADIOLOGY_TEAM
        team_roles = [role for role, n in RADIOLOGY_ROLES for _ in range(n)]
        team = [
            add_associate(role, "Radiology", DEMO_FACILITY, "IN", DEMO_MANAGER,
                          expiry_days=pinned[i] if pinned[i] is not None else 400, verified=True if i < 40 else None)
            for i, role in enumerate(team_roles)
        ]
        excluded = team[20]
        oig = next(c for c in excluded.credentials if c.credential_type.name == "OIG Exclusion Check")
        oig.verifications[:] = [Verification(
            checked_at=datetime.combine(today - timedelta(days=2), datetime.min.time()), source="OIG LEIE",
            result="excluded", details={"mock": True, "seeded": True, "exclusion_type": "1128(a)(1)"},
        )]

        # One radiologist whose NPI record is under a different name (the team roles end with the radiologists).
        npi_credential = next(c for c in team[-1].credentials if c.credential_type.name == "NPI Registration")
        npi_credential.verifications.append(Verification(
            checked_at=datetime.combine(today - timedelta(days=9), datetime.min.time()), source="NPPES",
            result="mismatch",
            details={"seeded": True, "npi": team[-1].npi, "reason": "Registry name does not match the name on file"},
        ))

        for i in range(TOTAL_ASSOCIATES - RADIOLOGY_TEAM):
            facility, state = FACILITIES[i % len(FACILITIES)]  # round-robin so every facility is staffed
            department = rng.choice(list(DEPARTMENTS))
            if facility == DEMO_FACILITY and department == "Radiology":
                department = "Emergency"  # keep the demo team at exactly 60
            slug = facility.lower().replace("'", "").replace(" ", "-")
            manager = "%s.%s@example.org" % (department.lower().replace(" ", "-"), slug)
            add_associate(rng.choice(DEPARTMENTS[department]), department, facility, state, manager)

        db.commit()
        refresh_statuses(db, today)
        return db.scalar(select(func.count(Associate.id))) or 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    print("Seeded %d associates." % seed(parser.parse_args().reset))
