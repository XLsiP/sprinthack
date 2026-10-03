# Beacon Credentialing Tracker

Verifies clinical staff credentials against public sources, tracks expiration dates, and alerts managers and HR before a credential lapses. Project details and conventions are in [CLAUDE.md](CLAUDE.md).

## Run it

Needs Python 3.11+ and Node 20+.

```bash
# backend: http://localhost:8000 (API docs at /docs)
cd api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py --reset
uvicorn main:app --reload --port 8000

# frontend: http://localhost:3000
cd web && npm install
npm run dev
```

Tests: `cd api && python -m pytest`

## What works

- Dashboard with status counts and an urgent-first credential list, scoped by role (Manager: the demo radiology team; HR: filter by facility, department, manager).
- All-credentials table and an associate profile with "Verify now".
- Verification: NPPES NPI Registry is real; ARRT, NMTCB, state licenses, BLS and OIG LEIE are mocks (labeled in `api/verify/`).
- Seed data: 1,500 synthetic associates across 11 facilities, including the 60-person radiology team.

## Not built yet

- Real OIG LEIE lookup (CSV download).
- Evidence PDFs, alert sending and the outbox page, scheduled re-verification, charts, deploy.

Seed NPIs are deliberately invalid so they can never match a real provider, which means NPPES verification reports them as not found.
