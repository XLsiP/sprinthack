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
  const name = <span className={cn("font-heading font-semibold", size === "lg" && "text-lg")}>Credentialing Tracker</span>;

  if (logo) {
    return (
      <span className={cn("flex items-center gap-3", className)}>
        {/* A plain <img>: a static file whose size we don't know ahead of time; next/image adds nothing here. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={logo} alt="Beacon Health System" className={cn("w-auto shrink-0", size === "lg" ? "h-12" : "h-8")} />
        <span aria-hidden className={cn("w-px shrink-0 bg-border", size === "lg" ? "h-8" : "h-6")} />
        <span className="whitespace-nowrap">{name}</span>
      </span>
    );
  }
  return (
    <span className={cn("flex flex-col text-left leading-tight", className)}>
      {name}
      <span className={cn("text-xs font-normal text-muted-foreground", compact && "max-sm:hidden")}>
        for Beacon Health System
      </span>
    </span>
  );
}
