import type { Verification } from "@/lib/api";

export type Tone = "success" | "error" | "warning";

export interface Feedback {
  tone: Tone;
  title: string;
  description?: string;
}

function reason(verification: Verification): string | undefined {
  const value = verification.details.reason;
  return typeof value === "string" ? value : undefined;
}

/** Toast content for one verification of the credential named `credential`. */
export function verificationFeedback(credential: string, verification: Verification): Feedback {
  const { result, source } = verification;
  switch (result) {
    case "verified":
      return { tone: "success", title: `${credential} verified`, description: `Confirmed with ${source}.` };
    case "excluded":
      return { tone: "error", title: `${credential}: excluded`, description: `Found on the ${source} exclusion list.` };
    case "not_found":
      return {
        tone: "error",
        title: `${credential}: not found`,
        description: reason(verification) ?? `No matching record at ${source}.`,
      };
    case "mismatch":
      return {
        tone: "error",
        title: `${credential}: mismatch`,
        description: reason(verification) ?? `The record at ${source} does not match.`,
      };
    case "error":
      return {
        tone: "warning",
        title: `${credential}: could not check`,
        description: reason(verification) ?? `Could not reach ${source}. Status is unchanged.`,
      };
  }
}

/** One summary toast for a "verify all" run. `names` maps credential id to its display name. */
export function summaryFeedback(verifications: Verification[], names: Map<number, string>): Feedback {
  const label = (v: Verification) => names.get(v.credential_id) ?? v.source;
  const verified = verifications.filter((v) => v.result === "verified").length;
  const failed = verifications.filter((v) => v.result !== "verified" && v.result !== "error").map(label);
  const unreachable = verifications.filter((v) => v.result === "error").map(label);
  const title = `${verified} of ${verifications.length} verified`;

  if (failed.length > 0) {
    const extra = unreachable.length > 0 ? ` Could not check: ${unreachable.join(", ")}.` : "";
    return { tone: "error", title, description: `Needs attention: ${failed.join(", ")}.${extra}` };
  }
  if (unreachable.length > 0) {
    return { tone: "warning", title, description: `Could not check: ${unreachable.join(", ")}.` };
  }
  return { tone: "success", title, description: "Every credential was confirmed at its source." };
}
