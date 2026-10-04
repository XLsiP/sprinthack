import { cn } from "@/lib/utils";

/**
 * Beacon's official logo | "Credentialing Tracker". The logo is only ever the file in public/partners/
 * (found by next.config.ts). Without it, a two-line wordmark names Beacon instead.
 * `compact` hides that fallback subtitle on phone widths so the header still fits.
 */
export function Brand({
  size = "md",
  compact = false,
  className,
}: {
  size?: "md" | "lg";
  compact?: boolean;
  className?: string;
}) {
  const logo = process.env.BEACON_LOGO;
  const large = size === "lg";
  // The name may wrap rather than overflow: cards clip overflow, so a nowrap name gets cut off.
  const name = <span className={cn("font-heading font-semibold", large && "text-lg")}>Credentialing Tracker</span>;

  if (logo) {
    return (
      // Large (password page): stack the logo above the name when the card is too narrow for one line.
      <span className={cn(large && "@container block w-full", className)}>
        <span
          className={cn(
            "flex items-center gap-3",
            large && "flex-col gap-2 text-center @min-[26rem]:flex-row @min-[26rem]:justify-center @min-[26rem]:gap-3",
          )}
        >
          {/* A plain <img>: a static file whose size we don't know ahead of time; next/image adds nothing here. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={logo} alt="Beacon Health System" className={cn("w-auto shrink-0", large ? "h-12" : "h-8")} />
          <span
            aria-hidden
            className={cn("w-px shrink-0 bg-border", large ? "hidden h-8 @min-[26rem]:block" : "h-6")}
          />
          {name}
        </span>
      </span>
    );
  }
  return (
    <span className={cn("flex flex-col leading-tight", large ? "items-center text-center" : "text-left", className)}>
      {name}
      <span className={cn("text-xs font-normal text-muted-foreground", compact && "max-sm:hidden")}>
        for Beacon Health System
      </span>
    </span>
  );
}
