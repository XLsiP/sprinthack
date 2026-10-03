# Design references

Screenshots and sketches that guide the UI in `/web`. Match their layout and feel; don't clone a real product, and don't use Beacon's logo or branding.

## Ground rules

- **Status colors, everywhere:** red = expired / excluded / verification failed, orange = ≤30 days, yellow = ≤90 days, green = valid, gray = not yet verified. The source of truth is `web/components/StatusBadge.tsx`.
- **Look:** calm, clean hospital-admin look: generous whitespace, clear hierarchy, readable tables.
- **Components:** shadcn/ui and Tailwind only, lucide-react icons, Recharts for charts.

## What to borrow

One row per screenshot. Under "Borrow", use one or more of: `layout`, `table`, `colors`, `chart`, `drawer`, `filters`.

| # | File | Source (URL) | Borrow | Notes |
| --- | --- | --- | --- | --- |
| 1 | [`01-tasks-data-table.png`](01-tasks-data-table.png) | https://ui.shadcn.com/examples/tasks | table | Dense credentials table: row checkboxes for bulk "Verify", sortable headers, icon + label status, and a `…` row menu. |
| 2 | [`02-dashboard-kpis-chart.png`](02-dashboard-kpis-chart.png) | https://ui.shadcn.com/examples/dashboard | layout, chart | Dashboard top: KPI cards with a small trend pill and one-line caption, then a full-width chart with a "3 months / 30 days / 7 days" range toggle. |
| 3 | [`03-kanban-lanes.png`](03-kanban-lanes.png) | https://example.crm.refine.dev/scrumboard/sales | layout | Lane per urgency bucket (Expired / ≤30 / ≤90 / Valid) with a count under each heading, as an alternative "board" view of the urgent list. |
| 4 | [`04-split-view.png`](04-split-view.png) | https://www.cultofmac.com/split-view | layout | List-plus-detail split: associates or credentials on the left, profile or evidence on the right, so managers can step through people without losing their place. |
| 5 | [`05-stores-table.png`](05-stores-table.png) | https://example.mui.admin.refine.dev/stores?pageSize=10&current=1 | table, colors | Outlined status pills with an icon (gray "Closed" / green "Open") map to our status badges; also the eye "view" action and the "Rows per page · 1–10 of 20" footer. |

### Adding a screenshot

1. Crop to the part you want to borrow, not the whole browser window.
2. Save as PNG in this folder, under ~500 KB, named `NN-short-name.png` (for example `03-expiry-table.png`).
3. Make sure no real names, emails or patient data are visible. Blur them if needed.
4. Fill in its row above: where it came from, and the one or two things to borrow.

## Key screen sketches

- [Dashboard](sketch-dashboard.md)
- [Associate profile](sketch-associate-profile.md)
- [Evidence drawer](sketch-evidence-drawer.md)
