import { Ban, CircleAlert, CircleCheck, CircleHelp, Clock, type LucideIcon, UserSearch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { AlertThreshold, CredentialStatus, VerificationResult } from "@/lib/api";
import { cn } from "@/lib/utils";

// Status colors used everywhere: red = expired/excluded, orange = within 30 days,
// yellow = within 90 days, green = valid, gray = not yet verified.
const TONES = {
  red: "bg-red-100 text-red-800",
  orange: "bg-orange-100 text-orange-800",
  yellow: "bg-yellow-100 text-yellow-800",
  green: "bg-green-100 text-green-800",
  gray: "bg-gray-100 text-gray-700",
} as const;

// Solid versions of the same colors, for chart bars.
const BAR_TONES = {
  red: "bg-red-500",
  orange: "bg-orange-500",
  yellow: "bg-yellow-400",
  green: "bg-green-500",
  gray: "bg-gray-400",
} as const;

// The same solid colors as CSS values, for Recharts (SVG fills can't take Tailwind classes).
const FILLS = {
  red: "var(--color-red-500)",
  orange: "var(--color-orange-500)",
  yellow: "var(--color-yellow-400)",
  green: "var(--color-green-500)",
  gray: "var(--color-gray-400)",
} as const;

/** Chart fill for a status, matching its badge. */
export function statusFill(status: CredentialStatus): string {
  return FILLS[STATUS[status].tone];
}

/** Chart fill for "not yet verified", matching `UnverifiedBadge`. */
export const UNVERIFIED_FILL = FILLS.gray;

export const STATUS: Record<CredentialStatus, { label: string; tone: keyof typeof TONES; icon: LucideIcon }> = {
  excluded: { label: "Excluded", tone: "red", icon: Ban },
  expired: { label: "Expired", tone: "red", icon: CircleAlert },
  verification_failed: { label: "Verification failed", tone: "red", icon: CircleAlert },
  expiring_30: { label: "Expires in 30 days", tone: "orange", icon: Clock },
  expiring_60: { label: "Expires in 60 days", tone: "yellow", icon: Clock },
  expiring_90: { label: "Expires in 90 days", tone: "yellow", icon: Clock },
  unverified: { label: "Not yet verified", tone: "gray", icon: CircleHelp },
  valid: { label: "Valid", tone: "green", icon: CircleCheck },
};

export function StatusBadge({ status }: { status: CredentialStatus }) {
  const { label, tone, icon: Icon } = STATUS[status];
  return (
    <Badge className={cn(TONES[tone])}>
      <Icon aria-hidden />
      {label}
    </Badge>
  );
}

export function UnverifiedBadge() {
  return (
    <Badge className={TONES.gray}>
      <CircleHelp aria-hidden />
      Not yet verified
    </Badge>
  );
}

/** Solid bar color for a status, matching its badge. */
export function statusBarClass(status: CredentialStatus): string {
  return BAR_TONES[STATUS[status].tone];
}

/** Marks a source whose lookup is simulated rather than a real integration. */
export function MockBadge() {
  return (
    <Badge variant="outline" className="h-4 px-1 text-[10px] text-muted-foreground" title="Simulated lookup, not a real check">
      MOCK
    </Badge>
  );
}

/** For an associate who holds no credentials yet. */
export function NoCredentialsBadge() {
  return <Badge className={TONES.gray}>No credentials</Badge>;
}

export const THRESHOLD: Record<AlertThreshold, { label: string; tone: keyof typeof TONES; icon: LucideIcon }> = {
  excluded: { label: "OIG exclusion", tone: "red", icon: Ban },
  expired: { label: "Expired", tone: "red", icon: CircleAlert },
  "30": { label: "30 days", tone: "orange", icon: Clock },
  "60": { label: "60 days", tone: "yellow", icon: Clock },
  "90": { label: "90 days", tone: "yellow", icon: Clock },
};

/** Which alert threshold fired, in the same colors as `StatusBadge`. */
export function ThresholdBadge({ threshold }: { threshold: AlertThreshold }) {
  const { label, tone, icon: Icon } = THRESHOLD[threshold];
  return (
    <Badge className={TONES[tone]}>
      <Icon aria-hidden />
      {label}
    </Badge>
  );
}

const RESULT: Record<VerificationResult, { label: string; tone: keyof typeof TONES; icon: LucideIcon }> = {
  verified: { label: "Verified", tone: "green", icon: CircleCheck },
  not_found: { label: "Not found", tone: "red", icon: CircleAlert },
  mismatch: { label: "Mismatch", tone: "red", icon: CircleAlert },
  excluded: { label: "Excluded", tone: "red", icon: Ban },
  // An unreachable source leaves the status unchanged, so this is gray rather than red.
  error: { label: "Could not check", tone: "gray", icon: CircleHelp },
};

// An "error" where the source matched several people: someone has to pick the right record.
const NEEDS_REVIEW = { label: "Needs review", tone: "yellow", icon: UserSearch } as const;

/** Outcome of one verification, in the same colors as `StatusBadge`. */
export function ResultBadge({ result, needsReview = false }: { result: VerificationResult; needsReview?: boolean }) {
  const { label, tone, icon: Icon } = needsReview ? NEEDS_REVIEW : RESULT[result];
  return (
    <Badge className={TONES[tone]}>
      <Icon aria-hidden />
      {label}
    </Badge>
  );
}
