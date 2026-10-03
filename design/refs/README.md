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
| 1 | `01-TODO.png` | TODO | TODO | TODO |
| 2 | `02-TODO.png` | TODO | TODO | TODO |
| 3 | `03-TODO.png` | TODO | TODO | TODO |
| 4 | `04-TODO.png` | TODO | TODO | TODO |
| 5 | `05-TODO.png` | TODO | TODO | TODO |
| 6 | `06-TODO.png` | TODO | TODO | TODO |

### Adding a screenshot

1. Crop to the part you want to borrow, not the whole browser window.
2. Save as PNG in this folder, under ~500 KB, named `NN-short-name.png` (for example `03-expiry-table.png`).
3. Make sure no real names, emails or patient data are visible. Blur them if needed.
4. Fill in its row above: where it came from, and the one or two things to borrow.

## Key screen sketches

- [Dashboard](sketch-dashboard.md)
- [Associate profile](sketch-associate-profile.md)
- [Evidence drawer](sketch-evidence-drawer.md)
