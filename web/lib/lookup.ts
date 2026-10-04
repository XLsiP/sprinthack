// Links to the sources' lookup pages for credentials a person verifies by hand.

import type { Credential } from "@/lib/api";

/** First and last name for a search form: the last word is the surname, the rest the first name. */
export function splitName(name: string): { first: string; last: string } {
  const parts = name.trim().split(/\s+/);
  return { first: parts.slice(0, -1).join(" "), last: parts[parts.length - 1] ?? "" };
}

/**
 * The lookup page for a credential, carrying the person's name.
 *
 * The name goes after "#", which the browser never sends to the site. The helper extension
 * (see /extension) reads it and fills in the search form. NMTCB's page also accepts the name
 * in the address itself, so that link works without the helper.
 */
export function lookupLink(c: Pick<Credential, "lookup_url" | "issuing_source" | "associate_name">): string | null {
  if (!c.lookup_url) return null;
  const { first, last } = splitName(c.associate_name);
  const hash = new URLSearchParams({ "bct-last": last, "bct-first": first }).toString();
  if (c.issuing_source === "NMTCB") {
    const query = new URLSearchParams({ LastName: last, FirstName: first });
    return `https://www.nmtcb.org/verification/results?${query}#${hash}`;
  }
  return `${c.lookup_url.split("#")[0]}#${hash}`;
}
