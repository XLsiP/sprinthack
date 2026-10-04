import { useId } from "react";

import { cn } from "@/lib/utils";

/**
 * The app's own mark: a rounded shield with a check, and light beams from its corner (a verified credential,
 * checked at the source). Original artwork; `app/icon.svg` is the same drawing for the browser tab.
 * Decorative: the text beside it names the app.
 */
export function Logo({ size = 28, className }: { size?: number; className?: string }) {
  // Unique gradient ids, so several logos on one page don't share (and lose) their fills.
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const shield = `logo-shield-${id}`;
  const shine = `logo-shine-${id}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden
      focusable="false"
      className={cn("shrink-0", className)}
    >
      <defs>
        <linearGradient id={shield} x1="5" y1="4" x2="23" y2="28" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2c5282" />
          <stop offset="1" stopColor="#1e3a5f" />
        </linearGradient>
        <linearGradient id={shine} x1="5" y1="5" x2="15" y2="17" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffffff" stopOpacity="0.22" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <g stroke="#14b8a6" strokeWidth="1.7" strokeLinecap="round">
        <path d="M25.6 7.4 29.4 6.9" opacity="0.55" />
        <path d="M25 4.6 27.8 1.9" />
        <path d="M22.4 3.4 23 0.9" opacity="0.55" />
      </g>
      <path
        d="M14 4.2 22.4 7.1c.7.2 1.1.8 1.1 1.5v6.8c0 5.9-3.9 10.6-9.5 12.9-5.6-2.3-9.5-7-9.5-12.9V8.6c0-.7.4-1.3 1.1-1.5L14 4.2Z"
        fill={`url(#${shield})`}
        stroke={`url(#${shield})`}
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M14 5.6 6.4 8.2v7.2c0 2.4.7 4.6 2 6.4L19 9.2 14 5.6Z" fill={`url(#${shine})`} />
      <path
        d="m9.4 16.1 3.2 3.2 6-7"
        stroke="#ffffff"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="m9.4 16.1 3.2 3.2 6-7" stroke="#5eead4" strokeWidth="0.9" strokeLinecap="round" strokeLinejoin="round" opacity="0.35" />
    </svg>
  );
}
