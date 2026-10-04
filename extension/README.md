# Credentialing Tracker helper (Chrome extension)

Every credential in the tracker is verified the same way: a person looks it up at the source and
confirms what it shows. This helper removes the typing. When you click **Open lookup** in the
tracker, it gets the person's result on screen, reads the expiry date off the page, and fills in the
tracker's form. You check it and click **Save and next**.

## What happens on each site

| Source | When you click Open lookup | What you do on the site | What is filled in for you |
| --- | --- | --- | --- |
| ARRT | The search page opens with the last and first name filled in | Tick "I'm not a robot", press Search, press **View Details** on the person | Expiry date (ARRT shows month and year, so the last day of that month) |
| ARDMS | The person's result opens | Nothing | Expiry date (the earliest, if they hold several credentials) |
| NMTCB | The person's result opens | Nothing | Expiry date |
| Michigan license | The lookup page opens, the name is filled in and the search runs | Nothing | License number and expiry date |

Then go back to the tracker tab. The form shows what was read, with a note saying which page it came
from. Check it against the page and click **Save and next**.

Only Michigan shows a number; ARRT, ARDMS and NMTCB do not show one on their result pages.

When the helper cannot fill the form:

- **Several people match** (Michigan, NMTCB): open the right person and it reads their page. On ARDMS,
  check the right one and type the date in yourself.
- **Nobody matches**: the form says so. Try another spelling on the site (a middle name or a former
  name) before choosing **Not found at source**.
- **The name on the page is not the person's**: the form still fills in but warns you in orange.

## What it does and does not do

- It acts only on a lookup page **that you opened from the tracker**, in your own browser.
- It **never** ticks or solves an "I'm not a robot" check. On ARRT you do that, press Search and
  press View Details yourself.
- It runs the search for you only on the Michigan lookup, which has no such check, and opens the
  person's page on NMTCB when exactly one person matches.
- It **never saves anything in the tracker**. It only fills in the form; a person saves.
- It runs on `arrt.org`, `nmtcb.org`, `myportal.inteleos.org` (ARDMS), the Michigan lookup at
  `aca-prod.accela.com/MILARA`, and the tracker itself (`localhost:3000` and `sprinthack-*.vercel.app`).
- The name travels in the part of the link after `#`, which browsers never send to the website.
- The one permission it asks for, `storage`, is how the result gets from the lookup tab to the
  tracker tab. What it keeps there is the latest result only: the dates and credential text, and the
  tracker's row number. No names. Nothing is sent anywhere else.

## Install (Chrome or Edge)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose this `extension` folder.

After pulling a new version of this folder, click the reload arrow on the extension's card, then
reload the tracker tab.

Without the extension, ARDMS and NMTCB still open on the result, ARRT and Michigan open blank, and
you type the number and date in yourself.

## If a site changes its page

- Name boxes and the sites the helper knows: `sites.js`.
- What is read off each result page: `readers.js`.
- The links the tracker builds: `web/lib/lookup.ts`. The form that receives the result:
  `web/lib/helper.ts` and `web/app/verify/page.tsx`.
- If the tracker moves to a new address, add it to the second block in `manifest.json`.
