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
| Deploy | Vercel (web) + Render (api, Docker); steps in `DEPLOY.md` |

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
/extension                # Chrome helper for the lookup sites: fills in the name, reads the result back into the Verify form (see its README)
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

Derived credential status: `valid`, `unverified`, `expiring_90`, `expiring_60`, `expiring_30`, `expired`, `verification_failed`, `excluded`. `unverified` is a credential of an expiring type with no expiry date on file and nothing verified yet (how every roster credential starts). Computed by `compute_status` in `api/status.py` from `expires_date` and the latest verification; precedence is excluded, expired, verification_failed (`not_found` or `mismatch`), then the expiry buckets. `error` results are ignored, so an unreachable source never clears an earlier exclusion or failure.

## API (FastAPI, prefix `/api`)

- `GET /health` (liveness check, returns `{"status": "ok"}`) · `GET /access` (is a password required, was the right one sent)
- `GET /associates?manager=&department=&facility=&status=&sort=&limit=&offset=` (`status` repeatable; `sort` is `urgency` (default) or `name`; total matches in the `X-Total-Count` header)
- `GET /associates/{id}` (with credentials + latest verifications)
- `GET /credentials?status=&expires_before=&manager=&department=&facility=&limit=&offset=` (most urgent first; `status` repeatable; `expires_before` exclusive; total matches in the `X-Total-Count` header)
- `POST /verify/credential/{id}` · `POST /verify/associate/{id}` · `POST /verify/all`
- `POST /verify/credential/{id}/manual` (record a lookup a person did at the source: `result` `verified` or `not_found`, plus `number`, `issued_date`, `expires_date`, `note`, `credentials_held`, `source_status`, and `source_details`, up to 12 other label/value pairs shown at the source; the `/verify` page in the web app is the queue for these)
- `GET /evidence/{verification_id}.pdf`
- `GET /alerts` · `POST /alerts/run` (manual alert sweep for the demo)
- `POST /alerts/credential/{id}/email` (email the associate's manager about an expiring credential; follow-up attempts are recorded)
- `GET /jobs/daily` (schedule on/off, next run, last run) · `POST /jobs/daily/run` (run the daily job now; 409 if one is already running)
- `GET /stats?manager=&department=&facility=` (counts by status, by facility, and a timeline of expirations over the next 90 days in 13 weekly buckets)

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
- Managers and HR can send an individual credential-expiry notice to the associate's manager from the credential and alert lists. The first recorded contact is an email; subsequent contacts are follow-ups. Attempts are retained in `credential_email_contacts`, including outbox-only attempts.
- The daily job (`api/scheduler.py`) re-verifies every credential, which refreshes each stored status, then runs the alert sweep. It runs at 06:00 Eastern by default; configure with `DAILY_JOB_HOUR`, `DAILY_JOB_MINUTE`, `SCHEDULER_TIMEZONE`, and turn the schedule off with `SCHEDULER_ENABLED=0`. Without `HR_EMAIL` it still re-verifies but skips the sweep.
- Email (`api/mailer.py`): with `RESEND_API_KEY` set, each recipient gets one HTML digest per sweep and those alert rows become `channel="email"`; otherwise, or if a send fails, they stay `channel="outbox"`. Reserved test addresses such as `@example.org` (all seed data) are never emailed unless `ALERT_EMAIL_OVERRIDE_TO` redirects every digest to one real inbox. `ALERT_EMAIL_MAX_PER_RUN` (default 10) caps emails per sweep, HR first; `ALERT_EMAIL_FROM` and `APP_URL` set the sender and the link base.
- `ACCESS_PASSWORD` (optional) puts a shared password on the API: sent as the `X-Access-Password` header, or `?access=` for links such as evidence PDFs. `GET /access` reports whether one is required. Unset means open, as in local development.
- `CORS_ORIGINS` is a comma-separated list of site URLs allowed to call the API (default `http://localhost:3000`); `CORS_ORIGIN_REGEX` optionally allows more by pattern.
- Set `HR_EMAIL` in the API environment for `POST /api/alerts/run`; the endpoint returns a configuration error if it is unset. Alerts are recorded in the outbox, one row per recipient.

## Design

- Visual references live in `design/refs/`. Match their layout and feel; don't clone a real product or Beacon's logo.
- Use shadcn/ui components and Tailwind only; no other CSS frameworks.
- Status colors everywhere: red = expired/excluded, orange = ≤30 days, yellow = ≤90 days, green = valid, gray = not yet verified.
- Calm, clean hospital-admin look: generous whitespace, clear hierarchy, readable tables.
- Key screens: dashboard (urgent items first + charts), associate profile (credential timeline + "Verify now"), evidence drawer (what/when/source + PDF download).
- Role switcher (Manager / HR) in the header for the demo instead of real auth. Manager asks which manager you are and for the access password again, then shows only that manager's team; the choice is kept in the browser. It is the one shared password, so it is not a per-manager login.
- The Verify page has a picker (search by name, filter by source, not-yet-verified or all); the chosen credential is in the address (`/verify?credential=<id>`), which is where the "Verify" buttons on the Credentials tab and the associate profile go.

## Data rules

- **The app's data is a real staff roster**, `api/rosters/kzo.csv` (Beacon Kalamazoo imaging: names, managers, and which source verifies each credential). It contains real names, so **this repo must stay private** and every deployment must set `ACCESS_PASSWORD`.
- **Nothing is invented about real people.** Roster credentials have no number, dates or verification and start `unverified`. Dates and results only come from a real lookup. Roles are assumed from which list a person is on, and manager emails are `first.last@example.org` placeholders, because the roster has neither.
- No PHI, and no NPIs for roster people.
- **Every roster credential is verified the same way: by a person** (`verify_method="manual"`), through the `/verify` queue. "Open lookup" takes them to the source: ARDMS and NMTCB links open on the person's result; on ARRT and Michigan the helper in `/extension` fills in the name (and runs the search on Michigan, which has no robot check). The helper then reads what the result page shows (credentials held, status, issue and expiry dates, the license number on Michigan, and everything else on the page including location) and pre-fills the form; the person checks it and saves, and it is all kept in that verification's `details`. The helper never saves anything itself. Mock verifiers never run on roster credentials.
- A real automatic Michigan verifier exists (`api/verify/michigan_lara.py`) but is switched off so all sources behave alike; `VERIFY_METHODS` in `api/roster.py` turns it on. ARRT requires a CAPTCHA on every search and must not be automated.
- A name search can match several people, so nothing is ever picked automatically for a real person. Tests must not call the live lookup sites (`conftest.py` blocks the Michigan one).
- `python seed.py --reset` loads the roster. `--synthetic` (or `SEED_SYNTHETIC=1`) generates 1,500 invented associates instead, with a 60-person radiology team and a mix of statuses; the tests use this and must never contain real names (`api/tests/fixtures/roster.csv` is invented). `--roster <csv>` or `ROSTER_FILE` loads a different roster: columns `first_name, last_name, manager, source`, with `source` one of `ARRT`, `ARDMS`, `NMTCB`, `MI_LARA` (see `api/roster.py`).
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
