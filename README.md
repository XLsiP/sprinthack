# Beacon Credentialing Tracker

## What it is

A credentialing tracker for Beacon Health System, built by Team G.A.S. at SprintHack@ND 2026. It keeps every imaging associate's credentials in one place: it shows what is expiring, helps a person check each credential at the board's website, keeps the evidence of each check, and alerts managers and HR before anything lapses. Project conventions for contributors are in [CLAUDE.md](CLAUDE.md).

Live site: TODO (team to confirm) · Demo video: TODO (team to confirm)

## The problem

- One imaging manager tracks about 60 associates' credentials by hand.
- Each role is checked on a different credentialing website (ARRT, ARDMS, NMTCB, the Michigan license lookup).
- Proof of each check is a paper printout filed in the employee's folder.
- The old system that flagged upcoming expirations was lost, so nothing warns anyone ahead of time.

**Goal:** save managers time. The tracker does not replace verification. A person still owns every decision about a real associate.

## What works today (Phase I)

- **Dashboard by role.** Managers get status tiles, charts, "Needs attention" and their own associates. HR gets a simpler overview: problems, credentials expiring within 90 days, a "Progress by manager" table, and the charts.
- **Credentials table and associate profile** with filters by manager, department and facility, a credential timeline, and "Verify now".
- **Verify page.** A picker (search by name, filter by source), then "Open lookup" goes to the board's site. The person records the result as verified or not found, with the expiry date.
- **Verify all.** Looks up ARDMS, NMTCB and Michigan LARA automatically, within the scope of the click (a manager's own team). Each source gets at most one request per second. When a name matches several people, or nobody, the credential is marked **needs review** and left for a person. Nothing is ever picked automatically.
- **Evidence drawer** for each verification (what was checked, when, and the source), with a **PDF download**.
- **Print-ready credential file** on the associate profile (one letter page).
- **Alerts** at 90, 60 and 30 days, on expiry, and on an OIG exclusion. They go to the manager and HR, and the same threshold is never sent twice for one credential. Alerts are logged in an outbox, and real email is sent only when configured.
- **Individual expiry notice.** From the credential and alert lists, email the associate's manager. Follow-ups are recorded.
- **Daily job** (06:00 Eastern by default): re-verifies credentials, then runs the alert sweep.
- **Manager / HR switch** in the header. Manager mode asks which manager you are.
- **Password page** (when the API is set to need one) and a **"Connecting…" screen** while the free-tier server wakes up.
- **Mobile layout:** pages reflow on phone screens.
- **Chrome helper (prototype)**, in [extension/](extension/README.md), loaded by hand in Chrome. It fills in the name on the ARRT and Michigan lookup pages. After the person passes the robot check and opens the result, it reads the expiry date (and the Michigan license number) back into the Verify form. The person checks the form and saves; the helper never saves anything itself.

## Real vs. human-in-the-loop vs. simulated

| Source / feature | How it works today |
| --- | --- |
| ARRT | **A person confirms.** ARRT puts a CAPTCHA on every search, and it is not bypassed or automated. The Chrome helper fills in the name and reads the result back. |
| ARDMS, NMTCB | **Real automatic lookup when someone clicks "Verify all"** (`api/verify/ardms.py`, `nmtcb_site.py`). Neither the daily job nor "verify one" runs it. A person can also check by hand. |
| Michigan LARA | **Real automatic lookup when someone clicks "Verify all"** (`api/verify/michigan_lara.py`). Limited to one search a second, and same-name matches are flagged `needs_review`. The always-on path (`VERIFY_METHODS` in `api/roster.py`) is empty, so on its own the daily job leaves Michigan to a person. |
| NPI Registry (NPPES) + OIG LEIE | **Real code, run only on the synthetic data.** The LEIE file is not part of the deploy, so OIG checks there report "could not check". |
| Synthetic 1,500-person dataset | Invented people. Their board results come from mocks labeled **MOCK** in `api/verify/`. |
| Manager / HR switch | **Demo toggle, not real logins.** It uses one shared password. |

## Architecture

```
Browser
  │
  ▼
Next.js web app (Vercel)          web/
  │  HTTPS, X-Access-Password header
  ▼
FastAPI API (Render, Docker)      api/
  ├── SQLite database              (DATABASE_URL can point elsewhere)
  ├── APScheduler daily job        re-verify → alert sweep
  ├── WeasyPrint                   evidence PDFs
  ├── Resend (optional)            alert emails; otherwise the outbox
  └── httpx → public sources       ARDMS, NMTCB, Michigan LARA, NPPES
```

## Run locally on Windows

Needs Python 3.11+ and Node 20+. The commands below use PowerShell, with the virtual environment in the repo root (`.venv`).

```powershell
# one-time setup, from the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r api\requirements.txt

# backend: http://localhost:8000 (API docs at /docs)
cd api
..\.venv\Scripts\Activate.ps1
$env:HR_EMAIL = "<an address for the alert sweep>"
python seed.py --reset                # load the roster
uvicorn main:app --reload --port 8000

# frontend: http://localhost:3000 (in a second terminal)
cd web
npm install
npm run dev
```

- **Reseed:** `python seed.py --reset`.
- **Synthetic data** (1,500 invented associates, for trying every feature): set `$env:SEED_SYNTHETIC = "1"` before reseeding, or run `python seed.py --reset --synthetic`.
- **Tests:** `cd api; python -m pytest`.
- **Evidence PDFs** need WeasyPrint's system libraries (Pango), which are hard to install on Windows. PDFs work in the deployed Docker build.
- **Deploying:** see [DEPLOY.md](DEPLOY.md).

Environment variables (names only; never commit values):

- `HR_EMAIL`: HR's address for alerts. Without it, the alert sweep is skipped.
- `ACCESS_PASSWORD`: puts a shared password on the API. Every deployment must set it.
- `RESEND_API_KEY`: turns on real alert emails through Resend. Without it, alerts stay in the outbox.
- `DATABASE_URL`: uses a different database (for example Postgres) instead of the local SQLite file.
- `SEED_SYNTHETIC`, `ROSTER_FILE`: choose what `seed.py` loads.
- Others: `CORS_ORIGINS`, `APP_URL`, `ALERT_EMAIL_FROM`, `ALERT_EMAIL_OVERRIDE_TO`, `ALERT_EMAIL_MAX_PER_RUN`, `SCHEDULER_ENABLED`, `DAILY_JOB_HOUR`, `DAILY_JOB_MINUTE`, `SCHEDULER_TIMEZONE`. See [CLAUDE.md](CLAUDE.md).

## Known limits

- **The data can reset.** The free hosting tier has no persistent disk, so the database is reseeded on every restart or redeploy, and recorded verifications are lost.
- **ARRT always needs a person** because of its CAPTCHA. ARDMS, NMTCB and Michigan run automatically only when someone clicks "Verify all", and same-name matches still need a person.
- **Automation is limited to these public lookups.** There is no Indiana license check for roster staff yet.
- **The roster is loaded by a script** (`seed.py`) from a CSV. There is no upload screen.
- **One shared demo password.** There are no per-person accounts.
- The Chrome helper is a prototype, loaded by hand.

## Phase II plan: NOT built yet

None of the following exists in the code today.

- **Beacon sign-in** (Firebase), replacing the shared password and the Manager / HR toggle.
- **A permanent Postgres database**, so data survives restarts.
- **Chrome helper, finished:** package and install it for Beacon staff, and extend it to more sites.
- **Roster import** from a spreadsheet or the HR system, instead of a script.
- **More roles and states:** nurses, physical therapists, dietitians, and Indiana licenses.
- **AI agents** that draft reminders and audit packets, with a person approving every action.

## Built vs. used

**We wrote:** the web app (`web/`), the API with its data model, status rules, verifiers, alert logic, evidence PDFs and daily job (`api/`), the synthetic data generator, the tests, and the Chrome helper (`extension/`).

**We used:**

- Open-source: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, lucide-react, Recharts, TanStack Query; FastAPI, Pydantic, SQLAlchemy, SQLite, APScheduler, httpx, WeasyPrint, pytest.
- Hosting and services: Vercel (web), Render (API), Resend (optional email).
- Public data sources: ARRT, ARDMS, NMTCB, Michigan LARA, the NPPES NPI Registry, and the OIG LEIE exclusion list.
- AI tools: Claude Code and GitHub Copilot.

## Team

Team G.A.S.: Grant Jeandron, Alex Dominguez, Steffano Vallenas.
