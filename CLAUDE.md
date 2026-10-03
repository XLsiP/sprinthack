# Beacon Credentialing Tracker

Hackathon project (2-day Innovation Sprint) for Beacon Health System (South Bend, IN). A web app that verifies clinical staff credentials against public sources, tracks expiration dates, stores verification evidence, and alerts managers and HR before a credential lapses.

## The problem we are solving

- One radiology manager manually tracks ~60 associates' credentials.
- Multiple portals: each role needs searches across separate public sites (state license, ARRT, NMTCB, BLS, OIG, NPI).
- Paper-heavy evidence: verification printouts go into paper employee files.
- No expiration control: the old system surfaced upcoming expirations; it was lost, so tracking is now manual.
- Beacon: 11 hospitals across Indiana and Michigan, 11,000+ associates. Indiana has no license reciprocity, so staff working across states may need checks in both.

## Stack

| Layer | Tool |
| --- | --- |
| Frontend | Next.js (App Router) + TypeScript |
| UI | Tailwind CSS + shadcn/ui, lucide-react icons |
| Charts | Recharts |
| Data fetching | TanStack Query against the FastAPI backend |
| Backend | Python 3.11+ + FastAPI + Pydantic v2 |
| ORM / DB | SQLAlchemy 2.0 + SQLite (`api/data/app.db`); can swap to Postgres via `DATABASE_URL` |
| Jobs | APScheduler (daily re-verification + alert sweep) |
| HTTP | httpx |
| Email | Resend (falls back to a logged "outbox" table when no API key) |
| Evidence PDFs | WeasyPrint |
| Deploy | Vercel (web) + Render/Railway (api) |

## Repo layout

```
/web                      # Next.js app (frontend team)
  app/
    page.tsx              # Manager/HR dashboard
    associates/[id]/      # Associate profile + credential timeline
    credentials/          # All credentials table with filters
    alerts/               # Alert log / outbox
  components/             # shared UI (StatusBadge, CredentialTable, EvidenceDrawer, RoleSwitcher)
  lib/api.ts              # typed fetch client for the FastAPI backend
/api                      # FastAPI app (backend team)
  main.py                 # app + router registration + CORS
  db.py                   # engine/session
  models.py               # SQLAlchemy models
  schemas.py              # Pydantic request/response models
  routers/                # associates.py, credentials.py, verify.py, alerts.py, evidence.py
  verify/                 # one adapter per source
    base.py               # Verifier protocol
    nppes.py              # REAL: NPPES NPI Registry API
    leie.py               # REAL: OIG LEIE exclusion CSV
    arrt.py, indiana_license.py, michigan_license.py, bls.py   # MOCKS
  alerts.py               # threshold logic + sending
  evidence.py             # PDF generation
  scheduler.py            # APScheduler jobs
  seed.py                 # synthetic data generator
/design/refs/             # screenshot references for UI
```

## Data model

Contract between frontend and backend; change only with team agreement.

- `associates`: id, name, npi, role, department, facility, state, manager_email
- `credential_types`: id, name, issuing_source, verify_method (`api` | `file` | `mock` | `manual`), renewal_months
- `role_requirements`: role, credential_type_id
- `credentials`: id, associate_id, credential_type_id, number, issued_date, expires_date, status
- `verifications`: id, credential_id, checked_at, source, result (`verified` | `not_found` | `excluded` | `mismatch` | `error`), details (JSON), evidence_path
- `alerts`: id, credential_id, threshold (`90` | `60` | `30` | `expired` | `excluded`), sent_to, sent_at, channel

Optional (nullable) columns: `associates.npi`, `credential_types.renewal_months`, `credentials.number`, `credentials.issued_date`, `credentials.expires_date` (empty for credentials that don't expire, such as the NPI and OIG checks), `verifications.evidence_path`.

Derived credential status: `valid`, `expiring_90`, `expiring_60`, `expiring_30`, `expired`, `verification_failed`, `excluded`. Computed by `compute_status` in `api/status.py` from `expires_date` and the latest verification; precedence is excluded, expired, verification_failed (`not_found` or `mismatch`), then the expiry buckets. `error` results are ignored, so an unreachable source never clears an earlier exclusion or failure.

## API (FastAPI, prefix `/api`)

- `GET /health` (liveness check, returns `{"status": "ok"}`)
- `GET /associates?manager=&department=&facility=&status=&sort=&limit=&offset=` (`status` repeatable; `sort` is `urgency` (default) or `name`; total matches in the `X-Total-Count` header)
- `GET /associates/{id}` (with credentials + latest verifications)
- `GET /credentials?status=&expires_before=`
- `POST /verify/credential/{id}` · `POST /verify/associate/{id}` · `POST /verify/all`
- `GET /evidence/{verification_id}.pdf`
- `GET /alerts` · `POST /alerts/run` (manual alert sweep for the demo)
- `GET /stats` (counts by status, by facility, upcoming-expiry timeline)

Backend generates OpenAPI at `/docs`. Keep `web/lib/api.ts` types in sync with `schemas.py`.

## Verifier interface

```python
class Verifier(Protocol):
    source: str
    def verify(self, associate: Associate, credential: Credential) -> VerificationResult: ...
# VerificationResult: result, source, details: dict, evidence_path: str | None
```

Mocks must look realistic (short delay, outcomes driven by seed data) and be clearly labeled as mocks in code. Each mock is a drop-in slot for a real integration later.

## Alerts

- Thresholds: 90, 60, 30 days before expiry, on expiry, and immediately on an OIG exclusion.
- Recipients: the associate's manager and HR. Never send the same threshold twice for one credential.

## Design

- Visual references live in `design/refs/`. Match their layout and feel; don't clone a real product or Beacon's logo.
- Use shadcn/ui components and Tailwind only; no other CSS frameworks.
- Status colors everywhere: red = expired/excluded, orange = ≤30 days, yellow = ≤90 days, green = valid, gray = not yet verified.
- Calm, clean hospital-admin look: generous whitespace, clear hierarchy, readable tables.
- Key screens: dashboard (urgent items first + charts), associate profile (credential timeline + "Verify now"), evidence drawer (what/when/source + PDF download).
- Role switcher (Manager / HR) in the header for the demo instead of real auth.

## Data rules

- Synthetic data only. No real staff names, real employee NPIs, or PHI in the repo.
- Seed ~1,500 associates across all 11 facilities, including a 60-person radiology department (the demo manager's team) with valid, expiring, expired, and one LEIE-excluded person.
- Gitignored: `.env*`, `api/data/`, `api/evidence/`, `*.db`, `node_modules/`, `.next/`, `__pycache__/`, `.venv/`.

## Running locally

```bash
# backend
cd api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py --reset
uvicorn main:app --reload --port 8000

# frontend
cd web && npm install
npm run dev          # http://localhost:3000, NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Conventions

- Python: type hints, Pydantic schemas for all I/O, SQL only through SQLAlchemy in `models.py`/routers.
- TypeScript: strict mode, no `any`; server state via TanStack Query.
- Dates are ISO `YYYY-MM-DD`.
- Small components; shared ones go in `web/components/`.

## Team workflow

- Branch per person/feature (`name/feature`), small PRs into `main`, pull often.
- Ownership: frontend owns `/web`, backend owns `/api`; the API section above is the contract.
- `main` must always start cleanly (both `npm run dev` and `uvicorn`).

## Demo priority (cut from the bottom if time runs short)

1. Dashboard with urgency buckets and filters by manager/department/facility
2. Verify one / verify all (NPPES + LEIE real, others mocked) with live result feedback
3. Evidence record per verification + PDF download
4. Alerts firing at thresholds (outbox view)
5. Charts, role views, scheduled re-verification, deploy to a live URL
