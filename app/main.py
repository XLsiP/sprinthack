from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import alerts, db, verify

STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


app = FastAPI(title="Credentialing", lifespan=lifespan)


class StaffIn(BaseModel):
    name: str
    role: str
    npi: Optional[str] = None
    email: Optional[str] = None
    manager_email: Optional[str] = None


class CredentialIn(BaseModel):
    type: str
    number: Optional[str] = None
    state: Optional[str] = None
    expires_on: date


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/staff")
def list_staff():
    conn = db.connect()
    return [dict(r) for r in conn.execute("SELECT * FROM staff ORDER BY name")]


@app.post("/api/staff", status_code=201)
def create_staff(staff: StaffIn):
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO staff (name, role, npi, email, manager_email) VALUES (?, ?, ?, ?, ?)",
            (staff.name, staff.role, staff.npi, staff.email, staff.manager_email),
        )
    return {"id": cur.lastrowid, **staff.model_dump()}


@app.post("/api/staff/{staff_id}/credentials", status_code=201)
def create_credential(staff_id: int, cred: CredentialIn):
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM staff WHERE id = ?", (staff_id,)).fetchone():
            raise HTTPException(404, "Staff member not found")
        cur = conn.execute(
            "INSERT INTO credentials (staff_id, type, number, state, expires_on) VALUES (?, ?, ?, ?, ?)",
            (staff_id, cred.type, cred.number, cred.state, cred.expires_on.isoformat()),
        )
    return {"id": cur.lastrowid, "staff_id": staff_id}


@app.get("/api/credentials")
def list_credentials():
    return alerts.list_credentials(db.connect())


@app.get("/api/alerts")
def list_alerts(days: int = alerts.WARNING_DAYS):
    return alerts.build_alerts(db.connect(), within_days=days)


@app.post("/api/staff/{staff_id}/verify")
def verify_staff(staff_id: int):
    """Check this staff member's credentials against the NPI Registry."""
    with db.connect() as conn:
        staff = conn.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone()
        if not staff:
            raise HTTPException(404, "Staff member not found")
        if not staff["npi"]:
            raise HTTPException(400, "No NPI on file for this staff member")
        try:
            provider = verify.lookup_npi(staff["npi"])
        except httpx.HTTPError as exc:
            raise HTTPException(502, "NPI Registry lookup failed: %s" % exc)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        results = []
        for cred in conn.execute("SELECT * FROM credentials WHERE staff_id = ?", (staff_id,)).fetchall():
            status = verify.check_credential(provider, cred)
            conn.execute(
                "UPDATE credentials SET verification_status = ?, verification_source = ?, verified_at = ? WHERE id = ?",
                (status, "NPI Registry", now, cred["id"]),
            )
            results.append({"credential_id": cred["id"], "type": cred["type"], "verification_status": status})
    return {"npi_found": provider is not None, "credentials": results}
