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
 * ARDMS and NMTCB accept the name in the address, so those links open on the person's result.
 * ARRT and Michigan do not: there the name goes after "#", which the browser never sends to the
 * site, and the helper extension (see /extension) reads it and fills in the search form.
 * Every link also carries the credential's id after "#", so the helper can hand the result it
 * reads back to the right row of the Verify form.
 */
export function lookupLink(
  c: Pick<Credential, "id" | "lookup_url" | "issuing_source" | "associate_name">,
): string | null {
  if (!c.lookup_url) return null;
  const { first, last } = splitName(c.associate_name);
  const hash = new URLSearchParams({ "bct-last": last, "bct-first": first, "bct-id": String(c.id) }).toString();
  if (c.issuing_source === "NMTCB") {
    const query = new URLSearchParams({ LastName: last, FirstName: first });
    return `https://www.nmtcb.org/verification/results?${query}#${hash}`;
  }
  if (c.issuing_source === "ARDMS") {
    // The ARDMS directory is run by Inteleos; its search page takes the name directly.
    const query = new URLSearchParams({ q: c.associate_name.trim() });
    return `https://myportal.inteleos.org/status-verification-directory.html?${query}#${hash}`;
  }
  return `${c.lookup_url.split("#")[0]}#${hash}`;
}
