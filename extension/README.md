# Credentialing Tracker helper (Chrome extension)

Every credential in the tracker is verified the same way: a person looks it up at the source and
confirms what it shows. This helper removes the typing. When you click **Open lookup** in the
tracker, it gets the person's result on screen, reads the expiry date off the page, and fills in the
tracker's form. You check it and click **Save and next**.

The tracker's **Verify all** button can look up ARDMS, NMTCB and Michigan by itself, since those
sites have no robot check. This helper is for everything else: every ARRT credential, anyone "Verify
all" could not settle (several people with the same name, or nobody under that name), and any
credential you would rather check by hand. It works the same on all four sites whether or not anyone
has clicked "Verify all".

## What happens on each site

| Source | When you click Open lookup | What you do on the site |
| --- | --- | --- |
| ARRT | The search page opens with the last and first name filled in | Tick "I'm not a robot", press Search, press **View Details** on the person |
| ARDMS | The person's result opens | Nothing |
| NMTCB | The person's result opens | Nothing |
| Michigan license | The lookup page opens, the name is filled in and the search runs | Nothing |

Then go back to the tracker tab. The form shows what was read. Check it against the page and click
**Save and next**.

## What is filled in

| Box on the form | ARRT | ARDMS | NMTCB | Michigan |
| --- | --- | --- | --- | --- |
| Credentials held | Credentials line, e.g. R.T.(R)(CT)(ARRT) | Each credential with its specialties | Certifications held | License type |
| Status at source | A sanction heading, if any | Active or other | ACTIVE or other | License status |
| Credential or ID number | not shown | not shown | not shown | License number |
| Issued on | not shown | Earliest "Valid from" | not shown | License issue date |
| Expires on | Valid Thru (last day of that month) | Earliest "Valid until" | Certified through | Expiration date |
| Also on the page | Location, country, valid thru, credential description, CE Biennium, CQR periods | Country, one line per credential | Location, certified through, "accurate as of" date | County, dates as shown |

"Also on the page" is a list under the boxes, in the site's own words. It is saved with the record
and appears in the evidence drawer and the evidence PDF. The Note box is left for your own remarks.

The location the sites show (city, state, zip, county) is recorded too. It is personal information
about real staff, which is one more reason the repo stays private and every deployment has a password.

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
  tracker tab. What it keeps there is the latest result only: what the page showed (credentials,
  status, dates, location) and the tracker's row number. No names. Nothing is sent anywhere else.

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
