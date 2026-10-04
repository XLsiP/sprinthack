# Credentialing Tracker helper (Chrome extension)

Every credential in the tracker is verified the same way: a person looks it up at the source and
records what they see. This helper removes the typing on the lookup sites. When you click
**Open lookup** in the tracker, the person's name is already filled in, or their result is already
on screen.

## What happens on each site

| Source | When you click Open lookup | What you do |
| --- | --- | --- |
| ARRT | The search page opens with the last and first name filled in | Tick "I'm not a robot", press Search |
| Michigan license | The lookup page opens, the name is filled in and the search runs | Nothing; read the result |
| ARDMS | The person's result opens directly (no helper needed) | Nothing; read the result |
| NMTCB | The person's result opens directly (no helper needed) | Nothing; read the result |

Then, in the tracker, enter the number and expiry date and click **Save and next**.

## What it does and does not do

- It acts only on a lookup page **that you opened from the tracker**, in your own browser.
- It **never** ticks or solves an "I'm not a robot" check. On ARRT you do that and press Search.
- It runs the search for you only on the Michigan lookup, which has no such check.
- It runs only on `arrt.org`, `nmtcb.org` and the Michigan lookup at `aca-prod.accela.com/MILARA`. It asks
  for no other permissions, sends nothing anywhere, and stores nothing.
- The name travels in the part of the link after `#`, which browsers never send to the website.

Reading the result back into the tracker is not built yet.

## Install (Chrome or Edge)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose this `extension` folder.

After pulling a new version of this folder, click the reload arrow on the extension's card.

Without the extension, ARDMS and NMTCB still open on the result; ARRT and Michigan open blank.

## If a site changes its page

The name boxes for each site are listed in `sites.js`. If the helper stops filling a site in, update
the selectors there. The ARDMS and NMTCB links are built in `web/lib/lookup.ts`.
