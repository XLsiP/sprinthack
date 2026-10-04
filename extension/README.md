# Credentialing Tracker helper (Chrome extension)

ARRT, ARDMS and NMTCB protect their credential search with an "I'm not a robot" check, so the
Credentialing Tracker cannot look people up on those sites by itself. This helper removes the typing:
when you click **Open lookup** in the tracker, it fills in the person's last and first name on the
lookup page for you.

## What it does and does not do

- It fills in the name boxes on a lookup page **that you opened from the tracker**.
- It does **not** tick or solve the "I'm not a robot" check, and it does not press Search. You do both.
- It only runs on `arrt.org`, `ardms.org` / `inteleos.org` and `nmtcb.org`. It asks for no other permissions,
  sends nothing anywhere, and stores nothing.
- The name travels in the part of the link after `#`, which browsers never send to the website.

Reading the result back into the tracker is not built yet.

## Install (Chrome or Edge)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose this `extension` folder.

## Use

1. In the tracker, open **Verify** and click **Open lookup** for a person.
2. The lookup page opens with the name filled in and a short note at the bottom of the page.
3. Tick "I'm not a robot" if asked, press Search, and read the result.
4. Back in the tracker, enter the ID number and expiry date and click **Save and next**.

Without the extension the lookup page simply opens blank, as before.

## If a site changes its page

The name boxes for each site are listed in `sites.js`. If the helper stops filling a site in, update
the selectors there. ARDMS's form has not been inspected (the site blocks automated page loads), so it
relies on finding boxes labelled "last" and "first"; check it on first use.
