# Deploying

The API runs on Render (Docker), the frontend on Vercel. Both deploy from `main` and redeploy on every push.

Do the steps in this order: the frontend needs the API's URL, and the API needs the frontend's URL.

## 1. API on Render

1. In the Render dashboard: **New → Blueprint**, pick this GitHub repo. Render reads [`render.yaml`](render.yaml) and proposes one web service, `beacon-credentialing-api`.
2. It asks for the variables marked "set in dashboard". Leave them all blank for now and click **Apply**.
3. Wait for the first build (several minutes). When it is live, open `https://<your-service>.onrender.com/api/health`; it should return `{"status":"ok"}`.
4. Copy the service URL (no trailing slash). You need it in step 2.

The API loads the built-in staff roster (real names) on start whenever the database is empty, so set `ACCESS_PASSWORD` before sharing the site. On Render this happens automatically; elsewhere set `SEED_IF_EMPTY=1`.

### If the service was created by hand instead of from the blueprint

A service made with **New → Web Service** does not read the variables from `render.yaml`, so add them yourself under **Environment**:

| Variable | Value |
| --- | --- |
| `CORS_ORIGINS` | the Vercel production URL, no trailing slash |
| `APP_URL` | the same URL |
| `HR_EMAIL` | `hr@example.org` |

Check **Settings → Runtime**. With **Docker**, leave "Docker Command" empty. With **Python 3**, evidence PDFs can fail because the Pango libraries are not guaranteed; if they do, recreate the service from the blueprint (a service's runtime cannot be changed).

Keep `HR_EMAIL` a placeholder: it is stored on every alert and shown on the public Alerts page. To receive alert emails yourself, set `RESEND_API_KEY` and `ALERT_EMAIL_OVERRIDE_TO` instead.

## 2. Frontend on Vercel

1. In the Vercel dashboard: **Add New → Project**, import this GitHub repo.
2. Set **Root Directory** to `web`. The framework is detected as Next.js; leave the build settings alone.
3. Add one environment variable: `NEXT_PUBLIC_API_URL` = the Render URL from step 1, with no trailing slash.
4. **Deploy**, then copy the production URL (for example `https://your-project.vercel.app`).

`NEXT_PUBLIC_API_URL` is baked in at build time. If you change it, redeploy.

## 3. Point the API at the frontend

In Render, open the service → **Environment**, and set:

| Variable | Value |
| --- | --- |
| `CORS_ORIGINS` | the Vercel production URL, no trailing slash |
| `APP_URL` | the same URL (used for links in alert emails) |

Save; Render redeploys. Until `CORS_ORIGINS` is set, the site loads but every data request is blocked by the browser.

## 4. Check it

- `https://<api>/api/stats` shows `"associates": 1500`.
- The Vercel site's dashboard shows numbers, an associate profile opens, **Verify** shows a toast, and an evidence PDF downloads.

## Environment variables (API)

| Variable | Needed | Purpose |
| --- | --- | --- |
| `CORS_ORIGINS` | yes | Comma-separated site URLs allowed to call the API. |
| `CORS_ORIGIN_REGEX` | no | Extra allowed origins by pattern, e.g. `https://your-project-.*\.vercel\.app` for Vercel preview deployments. |
| `APP_URL` | yes | Site URL used in alert email links. |
| `ACCESS_PASSWORD` | no | Shared password for the whole site. When set, every `/api` route except `/api/health` and `/api/access` requires it, and the site asks for it once per browser session. Set it before loading any real staff data. |
| `HR_EMAIL` | yes | HR recipient for alerts. Set to `hr@example.org` by the blueprint. |
| `RESEND_API_KEY` | no | Turns on real alert email. Without it, alerts stay in the outbox. |
| `ALERT_EMAIL_OVERRIDE_TO` | no | Send every alert email to this one inbox. Needed for a real send, because seed addresses are `@example.org`. |
| `SEED_IF_EMPTY` | no | `1` seeds an empty database at startup. Automatic on Render. |
| `ROSTER_FILE` | no | Path to a different roster CSV to load instead of the built-in one. If the file is missing, the built-in roster is used. |
| `SEED_SYNTHETIC` | no | `1` loads 1,500 invented associates instead of the roster. |
| `SCHEDULER_ENABLED` | no | `0` turns off the 06:00 daily job. |
| `MOCK_DELAY_MS` | no | Simulated lookup delay for mocked sources. |
| `DATABASE_URL` | no | Use Postgres instead of the built-in SQLite file. |

Secrets go in the Render dashboard only. Never commit them.

## Things to know before a demo

- **The free service sleeps** after about 15 minutes without traffic and takes around a minute to wake. Open the site a few minutes early.
- **Data resets on restart.** The free tier has no persistent disk, so verifications, alerts and PDFs created on the live site disappear when the service restarts or wakes, and the seed data comes back fresh.
- **OIG checks report "could not check".** The LEIE file (`api/data/UPDATED.csv`) is not part of the deploy.
- **A full run fails the NPI credentials.** "Verify all", "Run daily check" and the 06:00 job mark the seeded NPI credentials "Verification failed", because seed NPIs are deliberately invalid.
