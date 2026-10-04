// What the helper extension (see /extension) read on a lookup page, handed to the Verify form.
// The form only pre-fills from it; a person checks it and saves.

export type HelperResult = {
  id: number; // the credential the lookup was opened for
  source: string;
  credentials: string | null; // as the source writes them, e.g. R.T.(R)(CT)(ARRT)
  status: string | null;
  number: string | null;
  issued: string | null; // YYYY-MM-DD
  expires: string | null; // YYYY-MM-DD
  extra: { label: string; value: string }[]; // everything else on the page, in the site's own words
  hint: string | null; // how a value was worked out, when it was not copied as shown
  none: boolean; // the site said nobody matched
  mismatch: boolean; // the name on the page was not the person looked up
};

const MAX_AGE_MS = 30 * 60 * 1000;
const MAX_EXTRA = 12;

const text = (value: unknown, max: number): string | null =>
  typeof value === "string" && value.trim() ? value.trim().slice(0, max) : null;

/** A helper message turned into a result, or null if it is not one we can trust the shape of. */
export function parseHelperResult(data: unknown): HelperResult | null {
  if (typeof data !== "object" || data === null) return null;
  const message = data as Record<string, unknown>;
  if (message.from !== "bct-helper" || message.type !== "result") return null;
  if (typeof message.result !== "object" || message.result === null) return null;
  const r = message.result as Record<string, unknown>;
  if (typeof r.id !== "number" || typeof r.at !== "number" || Date.now() - r.at > MAX_AGE_MS) return null;
  const day = (value: unknown) => {
    const date = text(value, 10);
    return date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null;
  };
  // The same limits the API applies, so a long page cannot make the save fail.
  const extra: HelperResult["extra"] = [];
  for (const pair of Array.isArray(r.extra) ? r.extra : []) {
    if (!Array.isArray(pair) || extra.length >= MAX_EXTRA) continue;
    const label = text(pair[0], 60);
    const value = text(pair[1], 500);
    if (label && value && !extra.some((e) => e.label === label)) extra.push({ label, value });
  }
  return {
    id: r.id,
    source: text(r.source, 40) ?? "the lookup page",
    credentials: text(r.credentials, 300),
    status: text(r.status, 120),
    number: text(r.number, 64),
    issued: day(r.issued),
    expires: day(r.expires),
    extra,
    hint: text(r.hint, 200),
    none: r.none === true,
    mismatch: r.mismatch === true,
  };
}

/** Calls `onResult` with whatever the helper has read for this credential, now and as it arrives. */
export function listenForHelper(credentialId: number, onResult: (result: HelperResult) => void): () => void {
  const listener = (event: MessageEvent) => {
    if (event.source !== window || event.origin !== window.location.origin) return;
    const result = parseHelperResult(event.data);
    if (result && result.id === credentialId) onResult(result);
  };
  window.addEventListener("message", listener);
  window.postMessage({ from: "bct-page", type: "request" }, window.location.origin);
  return () => window.removeEventListener("message", listener);
}
