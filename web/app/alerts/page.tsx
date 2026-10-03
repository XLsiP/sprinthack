"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { AlertRunButton } from "@/components/AlertRunButton";
import { AlertTable } from "@/components/AlertTable";
import { useRole } from "@/components/Providers";
import { THRESHOLD } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api, type AlertThreshold, type CredentialStatus } from "@/lib/api";

const PAGE = 200;
const THRESHOLDS: AlertThreshold[] = ["excluded", "expired", "30", "60", "90"];
// Alerts only fire for these, so they cover nearly every alerted credential (renewed ones aside).
const ALERTED: CredentialStatus[] = ["excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90"];

export default function AlertsPage() {
  const { role } = useRole();
  const [threshold, setThreshold] = useState<AlertThreshold | null>(null);
  const [shown, setShown] = useState(PAGE);

  const alerts = useQuery({ queryKey: ["alerts"], queryFn: api.alerts });
  const credentials = useQuery({
    queryKey: ["credentials", "alerted"],
    queryFn: () => api.allCredentials({ status: ALERTED }),
  });
  const byId = useMemo(() => new Map((credentials.data ?? []).map((c) => [c.id, c])), [credentials.data]);

  const counts = useMemo(() => {
    const out = Object.fromEntries(THRESHOLDS.map((t) => [t, 0])) as Record<AlertThreshold, number>;
    for (const a of alerts.data ?? []) out[a.threshold] += 1;
    return out;
  }, [alerts.data]);
  const filtered = useMemo(
    () => (alerts.data ?? []).filter((a) => threshold === null || a.threshold === threshold),
    [alerts.data, threshold],
  );

  function pick(next: AlertThreshold | null) {
    setThreshold(next);
    setShown(PAGE);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Alerts</h1>
          <p className="text-sm text-muted-foreground">
            Sent to the associate&apos;s manager and HR at 90, 60 and 30 days before expiry, on expiry, and on an OIG
            exclusion. Each threshold is sent once per credential. Every alert is recorded here, whether it was emailed or kept in the outbox.
          </p>
        </div>
        {role === "hr" && <AlertRunButton />}
      </div>

      {alerts.data && alerts.data.length > 0 && (
        <div role="group" aria-label="Filter by threshold" className="flex flex-wrap gap-2">
          <Button size="sm" variant={threshold === null ? "default" : "outline"} aria-pressed={threshold === null} onClick={() => pick(null)}>
            All <span className="tabular-nums">{alerts.data.length.toLocaleString()}</span>
          </Button>
          {THRESHOLDS.map((t) => (
            <Button key={t} size="sm" variant={threshold === t ? "default" : "outline"} aria-pressed={threshold === t} onClick={() => pick(t)}>
              {THRESHOLD[t].label} <span className="tabular-nums">{counts[t].toLocaleString()}</span>
            </Button>
          ))}
        </div>
      )}

      {alerts.error && (
        <p role="alert" className="text-sm text-red-800">Could not load alerts ({alerts.error.message}).</p>
      )}
      {credentials.error && (
        <p role="alert" className="text-sm text-red-800">
          Could not load associate details ({credentials.error.message}). Alerts are listed by credential id.
        </p>
      )}

      {(alerts.data || !alerts.error) && (
        <Card>
          <CardContent>
            {!alerts.data ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
            ) : alerts.data.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No alerts sent yet. Alerts go out 90, 60 and 30 days before expiry, on expiry, and on an OIG exclusion.
              </p>
            ) : (
              <>
                <AlertTable alerts={filtered.slice(0, shown)} credentials={byId} />
                {filtered.length > shown && (
                  <div className="flex items-center justify-between pt-3 text-xs text-muted-foreground">
                    <span>
                      Showing {shown.toLocaleString()} of {filtered.length.toLocaleString()}, newest first.
                    </span>
                    <Button size="sm" variant="outline" onClick={() => setShown((n) => n + PAGE)}>
                      Show more
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
