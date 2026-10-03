import { Ban, CircleAlert, CircleCheck, CircleHelp, Clock, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { CredentialStatus } from "@/lib/api";
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

export const STATUS: Record<CredentialStatus, { label: string; tone: keyof typeof TONES; icon: LucideIcon }> = {
  excluded: { label: "Excluded", tone: "red", icon: Ban },
  expired: { label: "Expired", tone: "red", icon: CircleAlert },
  verification_failed: { label: "Verification failed", tone: "red", icon: CircleAlert },
  expiring_30: { label: "Expires in 30 days", tone: "orange", icon: Clock },
  expiring_60: { label: "Expires in 60 days", tone: "yellow", icon: Clock },
  expiring_90: { label: "Expires in 90 days", tone: "yellow", icon: Clock },
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
