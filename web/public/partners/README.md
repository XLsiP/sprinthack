Put Beacon's OFFICIAL logo here as beacon-logo.png, only with Beacon's permission. Do not screenshot or redraw it.

- `beacon-logo.svg` or `beacon-logo.png`: shown in the header, on the password page and on the printed credential file (the SVG wins if both are here). Without it the app shows only its "Credentialing Tracker" wordmark.
- `beacon-icon.png` (optional): the browser-tab icon. Without it the app uses a neutral icon (`public/app-icon.svg`).

The files are found when `npm run dev` or `npm run build` starts (`next.config.ts`), so restart the dev server after adding or removing one.
