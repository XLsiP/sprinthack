// MOCK: remove when backend alerts router merges.
// Synthetic stand-ins for GET /api/alerts and POST /api/alerts/run. lib/api.ts only uses these when the
// backend answers 404 for those routes, and it flags the result with `isMock: true`.

import type { Alert, AlertRunResult, AlertThreshold } from "./api";

const MANAGER = "radiology.manager@example.org";
const HR = "hr@example.org";

function daysAgo(days: number, hour: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
}

// [credential_id, threshold, days ago, hour sent]
const SENT: [number, AlertThreshold, number, number][] = [
  [412, "excluded", 0, 6],
  [87, "expired", 1, 6],
  [133, "30", 1, 6],
  [205, "30", 3, 6],
  [319, "60", 4, 6],
  [56, "60", 6, 6],
  [278, "90", 8, 6],
  [341, "90", 9, 6],
  [102, "90", 12, 6],
];

/** MOCK: one alert per recipient (manager and HR), newest first, like the real outbox. */
export function mockAlerts(): Alert[] {
  let id = 1;
  return SENT.flatMap(([credential_id, threshold, days, hour]) =>
    [MANAGER, HR].map((sent_to) => ({
      id: id++,
      credential_id,
      threshold,
      sent_to,
      sent_at: daysAgo(days, hour),
      channel: "outbox",
    })),
  );
}

/** MOCK: a sweep that finds nothing new, since every mock threshold has already been sent once. */
export function mockAlertRun(): AlertRunResult {
  return { sent: 0, by_threshold: {} };
}
