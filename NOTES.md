# NPPES and LEIE research

Findings for issue #4, based on the public CMS NPPES API and HHS-OIG LEIE
download/documentation. The LEIE CSV is a real public exclusion dataset; do
not check it into the repository. The project seed data must remain synthetic.

## NPPES NPI Registry

- API endpoint: `https://npiregistry.cms.hhs.gov/api/`
- Current API version used by the app: `2.1`; include `version=2.1` on requests.
- Lookup by NPI: `?version=2.1&number=<10-digit-NPI>`.
- Search by name: use `first_name` and `last_name`; optional geographic filters
  such as `state`, `city`, and `postal_code` narrow the candidate list. A name
  search can return multiple candidates and should not be treated as a unique
  identity match.
- Responses contain `result_count` and a `results` array. A no-match response
  has an empty `results` array. Useful record fields include `number`, `basic`,
  `addresses`, and `taxonomies`; taxonomy entries can include `license` and
  `state`.
- `basic.status == "A"` indicates an active NPI record, not that a professional
  license is currently in good standing. NPPES does not provide license
  expiration dates. A listed taxonomy license/state can be compared with a
  credential on file, but a match is not a substitute for checking the relevant
  state board.
- Use an HTTP timeout and handle non-success responses / network errors. The
  existing implementation uses a 10-second timeout and checks `raise_for_status()`.

Sources: [NPPES API documentation](https://npiregistry.cms.hhs.gov/api-page),
[NPI Registry API](https://npiregistry.cms.hhs.gov/api/).

## OIG LEIE exclusion list

- HHS-OIG publishes the complete active exclusion database as a CSV at
  `https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv`. The file is
  replaced with a current full database; OIG recommends using the full updated
  file rather than relying only on monthly supplements.
- Observed CSV columns:
  `LASTNAME`, `FIRSTNAME`, `MIDNAME`, `BUSNAME`, `GENERAL`, `SPECIALTY`,
  `UPIN`, `NPI`, `DOB`, `ADDRESS`, `CITY`, `STATE`, `ZIP`, `EXCLTYPE`,
  `EXCLDATE`, `REINDATE`, `WAIVERDATE`, `WVRSTATE`.
- For an individual, use `NPI` as the strongest available match when populated,
  and compare normalized first/middle/last names as a consistency check or
  fallback. For entities, use `BUSNAME`. Name-only matches can be ambiguous
  and should be treated cautiously. Some rows use `"0000000000"` as an NPI
  placeholder; do not treat that value as a real identifier.
- The complete active file excludes reinstated entities. OIG says monthly
  supplements contain additions and reinstatements for one month only; profile
  corrections are not for exclusion verification.
- OIG states that the Privacy Act prohibits distribution of SSNs. Do not store
  or add SSNs to the app or its synthetic seed data.
- Treat the downloaded CSV as runtime data (for example, under the gitignored
  `api/data/` directory), not a checked-in artifact. Refresh it when needed so
  exclusion checks are not against a stale snapshot.

Sources: [LEIE database and downloads](https://oig.hhs.gov/exclusions/leie-database-supplement-downloads/),
[LEIE quick tips](https://oig.hhs.gov/exclusions/leie-quick-tips-instructions/),
[current full CSV](https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv).
