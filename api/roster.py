"""Load a real staff roster (a CSV of names, managers and where each credential is verified).

A roster has no credential numbers or dates, so nothing is invented: each person gets one credential
per list they appear on, with no number, no dates and no verification. Those credentials are verified
by hand at the source (verify_method "manual"), or by a real integration where one exists (Michigan
LARA, verify_method "api"). The mock verifiers never run on them.

CSV columns: first_name, last_name, manager, source
"""
import csv
import re
from pathlib import Path

from sqlalchemy.orm import Session

from models import Associate, Credential, CredentialType

FACILITY = "Beacon Kalamazoo"
STATE = "MI"
DEPARTMENT = "Imaging"
COLUMNS = {"first_name", "last_name", "manager", "source"}

# Sources the app checks by itself ("api") instead of a person checking them through the lookup helper.
# None by default: every source is verified the same way, by a person, so the routine is identical
# everywhere. A real Michigan verifier exists (verify/michigan_lara.py); {"MI_LARA": "api"} turns it on.
VERIFY_METHODS: dict[str, str] = {}

# source in the CSV -> credential type, issuing source, the role we assume, renewal period, lookup page.
# The role is an assumption from which list a person is on; the roster itself has no job titles.
SOURCES = {
    "ARRT": ("ARRT Registration", "ARRT", "Radiologic technologist (ARRT)", 12,
             "https://www.arrt.org/pages/verify-credentials"),
    "ARDMS": ("ARDMS Registration", "ARDMS", "Sonographer (ARDMS)", 12,
              "https://www.ardms.org/verify-certification/"),
    "NMTCB": ("NMTCB Certification", "NMTCB", "Nuclear medicine technologist (NMTCB)", 12,
              "https://www.nmtcb.org/verification"),
    "MI_LARA": ("Michigan License", "Michigan LARA", "Michigan-licensed staff", 24,
                "https://aca-prod.accela.com/MILARA/GeneralProperty/PropertyLookUp.aspx?isLicensee=Y&TabName=APO"),
}
LOOKUP_URLS = {source: url for _, source, _, _, url in SOURCES.values()}


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def parse_manager(text: str) -> tuple[str, str, bool]:
    """Return (first, last, was_last_first). Accepts "Last,First M", "Last, First" and "First Last"."""
    text = " ".join(text.split())
    if "," in text:
        last, rest = (part.strip() for part in text.split(",", 1))
        return (rest.split()[0] if rest else ""), last, True
    parts = text.split()
    return parts[0], parts[-1], False


def canonical_managers(names: list[str]) -> dict[str, tuple[str, str]]:
    """Map every spelling of a manager to one (display name, placeholder email), matched by last name.

    The "Last,First" spelling wins when the same manager is also written "First Last", which is where
    the typos are. The email is a placeholder identifier at example.org; the roster has no addresses.
    """
    by_last: dict[str, tuple[str, str, bool]] = {}
    for name in names:
        first, last, formal = parse_manager(name)
        if _key(last) not in by_last or (formal and not by_last[_key(last)][2]):
            by_last[_key(last)] = (first, last, formal)
    out = {}
    for name in names:
        first, last, _ = by_last[_key(parse_manager(name)[1])]
        out[name] = ("%s %s" % (first, last), "%s.%s@example.org" % (_key(first), _key(last)))
    return out


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError("Roster is missing columns: %s" % ", ".join(sorted(missing)))
        rows = [{k: (row.get(k) or "").strip() for k in COLUMNS} for row in reader]
    rows = [row for row in rows if any(row.values())]
    for number, row in enumerate(rows, start=2):
        if not (row["first_name"] and row["last_name"] and row["manager"]):
            raise ValueError("Roster line %d is missing a name or manager" % number)
        if row["source"] not in SOURCES:
            raise ValueError("Roster line %d has unknown source %r" % (number, row["source"]))
    return rows


def load(db: Session, path: Path) -> int:
    """Add the roster's associates and credentials to `db` and return the number of people."""
    rows = read_rows(path)
    managers = canonical_managers([row["manager"] for row in rows])
    types = {
        key: CredentialType(
            name=name, issuing_source=source, verify_method=VERIFY_METHODS.get(key, "manual"), renewal_months=months,
        )
        for key, (name, source, _, months, _) in SOURCES.items()
    }
    db.add_all(types.values())

    people: dict[tuple[str, str], Associate] = {}
    held: set[tuple[tuple[str, str], str]] = set()
    for row in rows:
        person = (_key(row["first_name"]), _key(row["last_name"]))
        if person not in people:
            people[person] = Associate(
                name="%s %s" % (row["first_name"], row["last_name"]), npi=None, role=SOURCES[row["source"]][2],
                department=DEPARTMENT, facility=FACILITY, state=STATE, manager_email=managers[row["manager"]][1],
            )
            db.add(people[person])
        if (person, row["source"]) not in held:  # the same person listed twice under one source
            held.add((person, row["source"]))
            people[person].credentials.append(Credential(credential_type=types[row["source"]], status="unverified"))
    db.flush()
    return len(people)
