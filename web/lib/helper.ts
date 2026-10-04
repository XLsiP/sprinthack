// What the helper extension (see /extension) read on a lookup page, handed to the Verify form.
// The form only pre-fills from it; a person checks it and saves.

export type HelperResult = {
  id: number; // the credential the lookup was opened for
  source: string;
  expires: string | null; // YYYY-MM-DD
  number: string | null;
  summary: string; // what the page showed, in the site's own words
  hint: string | null; // how a value was worked out, when it was not copied as shown
  none: boolean; // the site said nobody matched
  mismatch: boolean; // the name on the page was not the person looked up
};

const MAX_AGE_MS = 30 * 60 * 1000;

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
  const expires = text(r.expires, 10);
  return {
    id: r.id,
    source: text(r.source, 40) ?? "the lookup page",
    expires: expires && /^\d{4}-\d{2}-\d{2}$/.test(expires) ? expires : null,
    number: text(r.number, 64),
    summary: text(r.summary, 300) ?? "",
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
