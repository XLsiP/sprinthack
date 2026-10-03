# Credentialing

Checks clinical staff credentials against public sources, tracks expiration dates, and alerts managers and HR before a credential lapses.

## Run it

Needs Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python seed.py                 # load fake demo data
uvicorn app.main:app --reload  # http://localhost:8000
```

- Dashboard: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Tests: `python -m pytest`
- Print today's alerts: `python -m app.alerts`

## What's here

| File | What it does |
| --- | --- |
| `app/main.py` | FastAPI routes |
| `app/db.py` | SQLite schema and connection (`credentials.db`, git-ignored) |
| `app/alerts.py` | Expiration status (expired / critical ≤30d / warning ≤90d / ok) and alert list |
| `app/verify.py` | Lookup against the CMS NPI Registry |
| `static/index.html` | Single-page dashboard, no build step |
| `seed.py` | Fake demo data |

## What works

- Add staff and credentials, see them sorted by expiration with a status.
- `GET /api/alerts?days=90` lists what is expired or expiring, and who should be told.
- "Verify" checks a staff member's NPI against the [NPI Registry](https://npiregistry.cms.hhs.gov/api-page) (free, no key) and matches license numbers and states.

## What's not built yet

- **Sending alerts.** `alerts.send()` only prints. Swap in email, Slack, or SMS, and run it on a schedule.
- **More sources.** The NPI Registry has no expiration dates and only covers licenses. Candidates: OIG exclusion list (LEIE), state licensing boards, Nursys.
- **Login and roles** (manager vs HR views).
- **Editing and deleting** records from the dashboard.

The seed staff are fake and have no NPI, so "Verify" needs a staff member added with a real NPI.

## Working together

```bash
git checkout -b your-feature
# make changes
git push -u origin your-feature   # then open a pull request
```
