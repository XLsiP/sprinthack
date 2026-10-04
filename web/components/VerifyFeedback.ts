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

/** An "error" where the source matched several different people: not an outage, someone has to pick one. */
export function needsReview(verification: Verification): boolean {
  return verification.result === "error" && verification.details.needs_review === true;
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
      if (needsReview(verification)) {
        return {
          tone: "warning",
          title: `${credential}: needs review`,
          description: reason(verification) ?? `More than one person matches at ${source}.`,
        };
      }
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
  const review = verifications.filter(needsReview).map(label);
  const unreachable = verifications.filter((v) => v.result === "error" && !needsReview(v)).map(label);
  const title = `${verified} of ${verifications.length} verified`;
  const notes = [
    review.length > 0 ? `Needs review: ${review.join(", ")}.` : "",
    unreachable.length > 0 ? `Could not check: ${unreachable.join(", ")}.` : "",
  ].filter(Boolean);

  if (failed.length > 0) {
    return { tone: "error", title, description: [`Needs attention: ${failed.join(", ")}.`, ...notes].join(" ") };
  }
  if (notes.length > 0) {
    return { tone: "warning", title, description: notes.join(" ") };
  }
  return { tone: "success", title, description: "Every credential was confirmed at its source." };
}
