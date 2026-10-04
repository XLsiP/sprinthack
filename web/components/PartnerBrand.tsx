"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

// Beacon's official logo, added only with Beacon's permission (see public/partners/README.md). Never redrawn here.
const PARTNER_LOGO = "/partners/beacon-logo.png";

/**
 * Beacon's logo, or the text "for Beacon Health System" when the file isn't there.
 * `compact` shortens the text fallback and the logo height on phone widths.
 */
export function PartnerBrand({ compact = false, className }: { compact?: boolean; className?: string }) {
  const img = useRef<HTMLImageElement>(null);
  const [failed, setFailed] = useState(false);

  // A server-rendered <img> can fail before React attaches onError, so check once after mounting too.
  useEffect(() => {
    const el = img.current;
    if (el && el.complete && el.naturalWidth === 0) setFailed(true);
  }, []);

  if (failed) {
    return (
      <span className={cn("text-sm whitespace-nowrap text-muted-foreground", className)}>
        {compact ? (
          <>
            <span className="sm:hidden">for Beacon</span>
            <span className="max-sm:hidden">for Beacon Health System</span>
          </>
        ) : (
          "for Beacon Health System"
        )}
      </span>
    );
  }
  return (
    // A plain <img> on purpose: the file may be missing, and onError swaps in the text fallback.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={img}
      src={PARTNER_LOGO}
      alt="Beacon Health System"
      onError={() => setFailed(true)}
      className={cn("h-auto max-h-7 w-auto", compact && "max-sm:max-h-5", className)}
    />
  );
}

/** [our brand] | [Beacon]: `children` is our side (the logo, with or without the name). */
export function CoBrand({
  children,
  compact = false,
  className,
}: {
  children: React.ReactNode;
  compact?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {children}
      <span aria-hidden className="h-6 w-px shrink-0 bg-border" />
      <PartnerBrand compact={compact} />
    </div>
  );
}
