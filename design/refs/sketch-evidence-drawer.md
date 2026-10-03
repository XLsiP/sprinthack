# Sketch: Evidence drawer

A side panel that answers "how do we know this credential is OK?": what was checked, when, against which source, and the proof. It opens from any credential row (associate profile, credentials table, dashboard). Not built yet.

```
                                   +---------------------------------------------+
  (page dimmed behind)             | Evidence                                [x] |
                                   |---------------------------------------------|
                                   | ARRT certification · Sam Ortiz              |
                                   | Number 123456 · Expires 2026-09-20          |
                                   | [Expired]                                   |
                                   |                                             |
                                   | -- Latest check --------------------------- |
                                   | Result     [✓ Verified]                     |
                                   | Source     ARRT   [MOCK]                    |
                                   | Checked    2026-10-01 09:14                 |
                                   |                                             |
                                   | -- Details -------------------------------- |
                                   | Name on record   Sam Ortiz                  |
                                   | Status           Active                     |
                                   | Discipline       Radiography                |
                                   | ...  (one row per key in `details`)         |
                                   |                                             |
                                   | [⬇ Download evidence PDF]                   |
                                   |                                             |
                                   | -- History -------------------------------- |
                                   | 2026-10-01  ARRT   Verified        PDF      |
                                   | 2026-07-01  ARRT   Verified        PDF      |
                                   | 2026-04-01  ARRT   Error           —        |
                                   |                                             |
                                   |                     [↻ Verify this again]   |
                                   +---------------------------------------------+
```

## Fields (from `Verification` in `web/lib/api.ts`)

| Shown as | Field | Notes |
| --- | --- | --- |
| Result | `result` | verified = green, not_found / mismatch / error = red, excluded = red with `Ban` icon |
| Source | `source` | add `[MOCK]` when the credential's `verify_method === "mock"` |
| Checked | `checked_at` | local date + time |
| Details | `details` | turn keys into labels (`license_status` → "License status"); show nested values as JSON |
| Download | `evidence_path` | button disabled with a "No PDF for this check" tooltip when null |

History needs every verification for one credential. The API currently returns only `last_verification`, so ask the backend team for `GET /api/credentials/{id}/verifications`, or drop History for the demo.

PDF link: `GET /api/evidence/{verification_id}.pdf` (in the CLAUDE.md API contract, not built yet).

## Components

- New: shadcn `Sheet` (`npx shadcn@latest add sheet`), opening from the right at ~420px wide and full width on mobile.
- New: `EvidenceDrawer({ credential, open, onOpenChange })` and `ResultBadge` (like `StatusBadge`, but for `VerificationResult`).
- Reuse: `StatusBadge`, `MockBadge` (from the profile sketch), `Button`.

## States

- **Never verified:** "Not yet verified" (gray) and a prominent "Verify now" button.
- **Loading history:** skeleton rows.
- **Verify again running:** the button spins, and the latest-check block updates when it finishes.
- **Excluded (OIG):** a red banner at the top: "On the OIG exclusion list. Do not schedule; notify HR."
