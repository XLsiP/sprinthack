# Sketch: Associate profile (`/associates/[id]`)

Everything about one person: who they are, which credentials they hold, and where each one stands over time. Built in `web/app/associates/[id]/page.tsx`; the timeline and the drawer link are not built yet.

```
+-------------------------------------------------------------------------------+
| [shield] Credentialing Tracker   Dashboard  Credentials  Alerts  [Manager|HR] |
+-------------------------------------------------------------------------------+
|                                                                               |
|  ← Back                                                                       |
|  Sam Ortiz                                           2 of 4 verified          |
|  Radiologic Technologist · Radiology · Memorial Hospital (IN) · NPI 1234…     |
|  Reports to radiology.manager@example.org                  [↻ Verify now]     |
|                                                                               |
|  +-- Credential timeline ----------------------------------------------------+|
|  |                    2025          2026    today       2027                 ||
|  |                                           |                               ||
|  | ARRT              [===========red========]|                               ||
|  | BLS                         [=====orange==|==]                            ||
|  | IN Radiology Lic. [=================green=|=================]             ||
|  | NPI               (no expiry)  ···········|············   [Valid]         ||
|  +---------------------------------------------------------------------------+|
|                                                                               |
|  +-- Credentials ------------------------------------------------------------+|
|  | Credential          Number    Expires              Status        Checked  ||
|  | ARRT                123456    2026-09-20 (13d ago) [Expired]     Oct 1    ||
|  |  ARRT  [MOCK]                                                             ||
|  | BLS                 BLS-7781  2026-10-28 (25d)     [≤30 days]    Oct 1    ||
|  | IN Radiology Lic.   RT-55012  2027-06-30 (270d)    [Valid]       Oct 1    ||
|  | NPI                 1234…     Does not expire      [Valid]       Oct 1    ||
|  +---------------------------------------------------------------------------+|
|          clicking a row opens the Evidence drawer →                           |
+-------------------------------------------------------------------------------+
```

## Timeline rules

- There's one row per credential, and the bar runs from `issued_date` to `expires_date`.
- The bar color follows `status`, using the same colors as `StatusBadge`.
- A vertical "today" line crosses all rows.
- When `expires_date` is null (NPI, OIG checks), draw a dotted line with the badge at the end.
- The x-axis spans the earliest issue date to 12 months after today.
- Sort rows most urgent first, the same order the API returns.

## Data

`GET /api/associates/{id}` → `AssociateDetail` (associate fields + `credentials: Credential[]`, each with `last_verification`).

## Components

- Existing: `CredentialTable` (`showAssociate={false}`; add a row click via its `action` prop or a new `onSelect`), `StatusBadge`, `UnverifiedBadge`, `Button`, `Card`.
- New: `CredentialTimeline` (Recharts horizontal range bars, or plain divs with Tailwind percent widths, whichever is simpler) and `MockBadge` for `verify_method === "mock"`.

## States

- **Loading:** skeleton header and timeline.
- **Not found / error:** "Could not load this associate" (already built), with a link back.
- **No credentials:** "No credentials on file for this role yet."
- **Verify now running:** the button spins, rows update when it finishes, and it shows "N of M verified".
