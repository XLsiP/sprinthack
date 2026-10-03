"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { AlertRunButton } from "@/components/AlertRunButton";
import { AlertTable } from "@/components/AlertTable";
import { DEMO_MANAGER, useRole } from "@/components/Providers";
import { THRESHOLD } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type AlertThreshold, type CredentialStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

const PAGE = 200;
const THRESHOLDS: AlertThreshold[] = ["excluded", "expired", "30", "60", "90"];
// Alerts only fire for these, so they cover nearly every alerted credential (renewed ones aside).
const ALERTED: CredentialStatus[] = ["excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90"];

/** Loading, empty and error text inside a card, styled like the Dashboard's section messages. */
function SectionMessage({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("space-y-1 py-8 text-center text-sm text-muted-foreground", className)}>{children}</div>;
}

function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {children}
    </p>
  );
}

/** Placeholder rows at about the height of the loaded table, so the card doesn't jump when data arrives. */
function TableSkeleton() {
  return (
    <div className="space-y-2" role="status" aria-label="Loading alerts">
      <Skeleton className="h-6 w-full" />
      {Array.from({ length: 8 }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export default function AlertsPage() {
  const { role } = useRole();
  const [threshold, setThreshold] = useState<AlertThreshold | null>(null);
  const [shown, setShown] = useState(PAGE);
  const [sweepError, setSweepError] = useState<string | null>(null);

  const isManager = role === "manager";

  const alerts = useQuery({ queryKey: ["alerts"], queryFn: api.alerts });
  const credentials = useQuery({
    queryKey: ["credentials", "alerted", role],
    queryFn: () => api.allCredentials({ status: ALERTED, manager: isManager ? DEMO_MANAGER : undefined }),
    placeholderData: keepPreviousData,
  });
  const byId = useMemo(() => new Map((credentials.data ?? []).map((c) => [c.id, c])), [credentials.data]);

  // One row per recipient, so a manager's alerts are exactly the rows sent to them.
  const visible = useMemo(
    () => (alerts.data ? alerts.data.filter((a) => !isManager || a.sent_to === DEMO_MANAGER) : undefined),
    [alerts.data, isManager],
  );
  const counts = useMemo(() => {
    const out = Object.fromEntries(THRESHOLDS.map((t) => [t, 0])) as Record<AlertThreshold, number>;
    for (const a of visible ?? []) out[a.threshold] += 1;
    return out;
  }, [visible]);
  const filtered = useMemo(
    () => (visible ?? []).filter((a) => threshold === null || a.threshold === threshold),
    [visible, threshold],
  );
  // Wait for the associate lookup too (or its failure), so rows don't flash "Credential #id" before names arrive.
  const loading = (!visible && !alerts.error) || (visible !== undefined && credentials.isPending);

  function pick(next: AlertThreshold | null) {
    setThreshold(next);
    setShown(PAGE);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="max-w-prose text-sm text-muted-foreground">
            Sent to the associate&apos;s manager and HR at 90, 60 and 30 days before expiry, on expiry, and on an OIG
            exclusion. Each threshold is sent once per credential. Every alert is recorded here, whether it was emailed or
            kept in the outbox.
          </p>
        </div>
        {role === "hr" && <AlertRunButton onError={setSweepError} onSuccess={() => setSweepError(null)} />}
      </div>

      {alerts.error &&
        (visible ? (
          <ErrorBanner>Could not refresh alerts ({alerts.error.message}). Showing the last loaded list.</ErrorBanner>
        ) : (
          <ErrorBanner>Could not reach the API ({alerts.error.message}). Is the backend running on port 8000?</ErrorBanner>
        ))}
      {credentials.error && visible && (
        <ErrorBanner>
          Could not load associate details ({credentials.error.message}). Alerts are listed by credential id.
        </ErrorBanner>
      )}
      {role === "hr" && sweepError && <ErrorBanner>{sweepError}</ErrorBanner>}

      <Card>
        <CardHeader>
          <CardTitle>Alert log</CardTitle>
          <CardDescription>
            {loading && <Skeleton className="h-5 w-72 max-w-full" />}
            {!loading &&
              visible &&
              `${isManager ? "Sent to you for your team" : "All facilities"} · ${visible.length.toLocaleString()} ${
                visible.length === 1 ? "alert" : "alerts"
              }, newest first`}
          </CardDescription>
          {loading && (
            <div className="flex flex-wrap gap-2 pt-2" aria-hidden>
              {Array.from({ length: THRESHOLDS.length + 1 }, (_, i) => (
                <Skeleton key={i} className="h-7 w-24 rounded-lg" />
              ))}
            </div>
          )}
          {!loading && visible && visible.length > 0 && (
            <div role="group" aria-label="Filter by threshold" className="flex flex-wrap gap-2 pt-2">
              {([null, ...THRESHOLDS] as (AlertThreshold | null)[]).map((t) => {
                const active = threshold === t;
                return (
                  <Button
                    key={t ?? "all"}
                    size="sm"
                    variant={active ? "default" : "outline"}
                    aria-pressed={active}
                    onClick={() => pick(t)}
                  >
                    {t === null ? "All" : THRESHOLD[t].label}
                    <span className={cn("tabular-nums", active ? "opacity-70" : "text-muted-foreground")}>
                      {(t === null ? visible.length : counts[t]).toLocaleString()}
                    </span>
                  </Button>
                );
              })}
            </div>
          )}
        </CardHeader>
        <CardContent>
          {loading ? (
            <TableSkeleton />
          ) : !visible ? (
            <SectionMessage>
              <p>Couldn&apos;t load alerts.</p>
            </SectionMessage>
          ) : visible.length === 0 ? (
            <SectionMessage>
              <p className="font-medium text-foreground">{isManager ? "No alerts sent to you yet." : "No alerts sent yet."}</p>
              <p>Alerts go out 90, 60 and 30 days before expiry, on expiry, and on an OIG exclusion.</p>
            </SectionMessage>
          ) : filtered.length === 0 && threshold !== null ? (
            <SectionMessage>
              <p className="font-medium text-foreground">No {THRESHOLD[threshold].label} alerts.</p>
              <Button variant="link" size="sm" onClick={() => pick(null)}>
                Show all alerts
              </Button>
            </SectionMessage>
          ) : (
            <>
              {/* The department · facility and issuing-source lines (3rd and 4th columns) wrap when space runs out; below
                  lg (and at high zoom) the Sent time and credential name may wrap too, so the long manager emails in
                  Recipient fit without scrolling. Names and emails stay on one line. Scoped to this page. */}
              <div
                className={cn(
                  "[&_td:nth-child(3)_div]:whitespace-normal [&_td:nth-child(4)_div]:whitespace-normal",
                  // min-w keeps the date whole, so Sent breaks at the space (date over time), not at its hyphens.
                  "max-lg:[&_td:nth-child(1)]:min-w-[6.5rem] max-lg:[&_td:nth-child(1)]:whitespace-normal max-lg:[&_td:nth-child(4)]:whitespace-normal",
                  credentials.isPlaceholderData && "opacity-60",
                )}
                aria-busy={alerts.isFetching || credentials.isFetching}
              >
                <AlertTable alerts={filtered.slice(0, shown)} credentials={byId} />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 pt-3 text-sm text-muted-foreground">
                <span className="tabular-nums">
                  {filtered.length > shown
                    ? `Showing ${shown.toLocaleString()} of ${filtered.length.toLocaleString()}`
                    : `Showing all ${filtered.length.toLocaleString()}`}
                </span>
                {filtered.length > shown && (
                  <Button size="sm" variant="outline" onClick={() => setShown((n) => n + PAGE)}>
                    Show more
                  </Button>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
