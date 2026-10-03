"use client";

import { useState } from "react";

import { STATUS, StatusBadge, statusBarClass } from "@/components/StatusBadge";
import type { Credential } from "@/lib/api";

const DAY = 86_400_000;

/** Milliseconds for an ISO `YYYY-MM-DD` date, at UTC midnight. */
function ms(isoDate: string): number {
  return Date.parse(`${isoDate}T00:00:00Z`);
}

function todayMs(): number {
  const now = new Date();
  return Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
}

/**
 * One bar per credential from issue date to expiry, colored by status, with a "today" line.
 * The axis runs from the earliest issue date to 12 months after today.
 */
export function CredentialTimeline({ credentials }: { credentials: Credential[] }) {
  const [today] = useState(todayMs);
  const issued = credentials.flatMap((c) => (c.issued_date ? [ms(c.issued_date)] : []));
  const start = Math.min(today - 365 * DAY, ...issued);
  const end = today + 365 * DAY;
  const percent = (t: number) => Math.min(100, Math.max(0, ((t - start) / (end - start)) * 100));

  const years: number[] = [];
  for (let y = new Date(start).getUTCFullYear() + 1; Date.UTC(y, 0, 1) < end; y++) years.push(y);
  const todayLine = (
    <div className="absolute inset-y-0 w-px bg-foreground/60" style={{ left: `${percent(today)}%` }} aria-hidden />
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-[13rem_1fr] sm:gap-x-4">
      <div className="hidden sm:block" />
      <div className="relative h-6 text-xs text-muted-foreground" aria-hidden>
        {years
          .filter((y) => Math.abs(percent(Date.UTC(y, 0, 1)) - percent(today)) > 12) // leave room for the Today label
          .map((y) => (
            <span key={y} className="absolute top-0 -translate-x-1/2" style={{ left: `${percent(Date.UTC(y, 0, 1))}%` }}>
              {y}
            </span>
          ))}
        <span
          className="absolute top-0 -translate-x-1/2 rounded bg-foreground px-1 text-background"
          style={{ left: `${percent(today)}%` }}
        >
          Today
        </span>
      </div>

      {credentials.map((c) => {
        const left = percent(c.issued_date ? ms(c.issued_date) : start);
        const right = c.expires_date ? percent(ms(c.expires_date)) : 100;
        const summary = c.expires_date
          ? `${c.issued_date ?? "issue date unknown"} to ${c.expires_date}`
          : "does not expire";
        return (
          <div key={c.id} className="contents">
            <div className="flex flex-col justify-center pt-2 sm:py-1.5">
              <span className="text-sm leading-tight">{c.credential_type}</span>
              <span className="text-xs text-muted-foreground">
                {STATUS[c.status].label} · {summary}
              </span>
            </div>
            <div className="relative h-9 border-b sm:border-b-0" title={`${c.credential_type}: ${summary}, ${STATUS[c.status].label}`}>
              {years.map((y) => (
                <div
                  key={y}
                  className="absolute inset-y-0 w-px bg-border"
                  style={{ left: `${percent(Date.UTC(y, 0, 1))}%` }}
                  aria-hidden
                />
              ))}
              {c.expires_date ? (
                <div
                  className={`absolute top-2.5 h-4 rounded-sm ${statusBarClass(c.status)}`}
                  style={{ left: `${left}%`, width: `${Math.max(right - left, 0.75)}%` }}
                />
              ) : (
                <>
                  <div className="absolute inset-x-0 top-1/2 border-t-2 border-dotted border-muted-foreground/50" />
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 bg-card pl-1.5">
                    <StatusBadge status={c.status} />
                  </div>
                </>
              )}
              {todayLine}
            </div>
          </div>
        );
      })}
    </div>
  );
}
