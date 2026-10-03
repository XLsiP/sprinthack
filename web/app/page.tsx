"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { CredentialTable } from "@/components/CredentialTable";
import { useScope } from "@/components/ScopeFilters";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type CredentialStatus, type Stats } from "@/lib/api";

const URGENT: CredentialStatus[] = [
  "excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90",
];

function tiles(stats: Stats) {
  const s = stats.by_status;
  return [
    { label: "Expired or excluded", value: s.expired + s.excluded, accent: "border-l-red-500" },
    { label: "Verification failed", value: s.verification_failed, accent: "border-l-red-500" },
    { label: "Expiring in 30 days", value: s.expiring_30, accent: "border-l-orange-500" },
    { label: "Expiring in 31–90 days", value: s.expiring_60 + s.expiring_90, accent: "border-l-yellow-400" },
    { label: "Valid", value: s.valid, accent: "border-l-green-500" },
    { label: "Not yet verified", value: stats.unverified, accent: "border-l-gray-400" },
  ];
}

export default function Dashboard() {
  const { scope, filters } = useScope();
  const queryClient = useQueryClient();
  const stats = useQuery({ queryKey: ["stats", scope], queryFn: () => api.stats(scope) });
  const urgent = useQuery({
    queryKey: ["credentials", scope, "urgent"],
    queryFn: () => api.credentials({ ...scope, status: URGENT, limit: 50 }),
  });
  const verifyAll = useMutation({
    mutationFn: () => api.verifyAll(scope),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const error = stats.error ?? urgent.error ?? verifyAll.error;
  const urgentTotal = stats.data ? URGENT.reduce((n, s) => n + stats.data.by_status[s], 0) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          {filters}
        </div>
        <div className="flex items-center gap-3">
          {verifyAll.data && (
            <p className="text-sm text-muted-foreground" role="status">
              Checked {verifyAll.data.checked.toLocaleString()} credentials
            </p>
          )}
          <Button onClick={() => verifyAll.mutate()} disabled={verifyAll.isPending}>
            <RefreshCw className={verifyAll.isPending ? "animate-spin" : undefined} aria-hidden />
            {verifyAll.isPending ? "Verifying…" : "Verify all"}
          </Button>
        </div>
      </div>

      {error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Could not reach the API ({error.message}). Is the backend running on port 8000?
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {stats.data &&
          tiles(stats.data).map((tile) => (
            <Card key={tile.label} className={`border-l-4 ${tile.accent}`}>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">{tile.value.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground">{tile.label}</div>
              </CardContent>
            </Card>
          ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Needs attention</CardTitle>
          <CardDescription>
            {stats.data &&
              `${stats.data.associates.toLocaleString()} associates · ${urgentTotal.toLocaleString()} credentials need attention` +
                (urgentTotal > 50 ? ", showing the 50 most urgent" : "")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {urgent.data ? (
            <CredentialTable credentials={urgent.data} />
          ) : (
            !error && <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
