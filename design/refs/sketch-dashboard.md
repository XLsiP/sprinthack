# Sketch: Dashboard (`/`)

The landing page for managers and HR. It puts urgent items first, then the bigger picture. Built in `web/app/page.tsx`; the charts are not built yet.

```
+-------------------------------------------------------------------------------+
| [shield] Credentialing Tracker   Dashboard  Credentials  Alerts  [Manager|HR] |
+-------------------------------------------------------------------------------+
|                                                                               |
|  Dashboard                                                   [↻ Verify all]   |
|  Manager: "Your team: Radiology, Memorial Hospital"                           |
|  HR:      [All facilities v] [All departments v] [All managers v]             |
|                                                                               |
|  +----------+ +----------+ +----------+ +----------+ +----------+ +---------+ |
|  |▌  57     | |▌  81     | |▌ 112     | |▌ 341     | |▌ 4,793   | |▌ 1,441  | |
|  |▌ Expired | |▌ Verif.  | |▌ ≤30 days| |▌ 31–90   | |▌ Valid   | |▌ Not    | |
|  |▌ /excl.  | |▌ failed  | |▌         | |▌ days    | |▌         | |▌ verif. | |
|  +----------+ +----------+ +----------+ +----------+ +----------+ +---------+ |
|    red          red          orange       yellow       green        gray      |
|                                                                               |
|  +-- Upcoming expirations ---------------+ +-- By facility -----------------+ |
|  |  ▇                                    | | Memorial      ████████▒▒░      | |
|  |  ▇  ▇     ▇                           | | Elkhart       ██████▒░         | |
|  |  ▇  ▇  ▇  ▇  ▇  ▇                     | | Three Rivers  ████▒            | |
|  |  Oct Nov Dec Jan Feb Mar ...          | | ...  (stacked by status color) | |
|  +---------------------------------------+ +--------------------------------+ |
|                                                                               |
|  +-- Needs attention --------------------------------------------------------+|
|  | 60 associates · 23 credentials need attention                             ||
|  |                                                                           ||
|  | Associate          Credential        Number    Expires       Status   Last||
|  | Jamie Merrow       OIG Exclusion     —         Does not exp. [Excluded]   ||
|  |  Radiology·Memorial  OIG LEIE                                             ||
|  | Sam Ortiz          ARRT              123456    2026-09-20    [Expired]    ||
|  | ...                                            (12d ago)                  ||
|  +---------------------------------------------------------------------------+|
+-------------------------------------------------------------------------------+
```

## Data

| Area | Source |
| --- | --- |
| Tiles | `GET /api/stats` → `by_status`, `unverified` |
| Upcoming expirations | `Stats.timeline` (`{ month, count }[]`) |
| By facility | `Stats.by_facility` (`{ facility, total, by_status }[]`), HR view only |
| Needs attention | `GET /api/credentials?status=…&limit=50`, sorted most urgent first |

## Components

- Existing: `Header`, `RoleSwitcher`, `ScopeFilters` (`useScope`), `StatusBadge`, `CredentialTable`, shadcn `Card`, `Button`, `Select`, `Table`.
- New: `ExpiryTimelineChart` (Recharts `BarChart`) and `FacilityChart` (stacked horizontal `BarChart` in the status colors).

## States

- **Loading:** tiles and charts show skeletons, and the table shows "Loading…".
- **Empty:** "Nothing needs attention 🎉" in the table card, while the tiles still show counts.
- **API down:** the red alert banner "Could not reach the API…" (already built).
- **Verify all running:** the button spins and is disabled; afterward it shows "Checked N credentials".
