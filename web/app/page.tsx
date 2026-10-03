"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, X } from "lucide-react";
import { useState } from "react";

import { AssociateTable, type AssociateSort } from "@/components/AssociateTable";
import { CredentialTable } from "@/components/CredentialTable";
import { useScope } from "@/components/ScopeFilters";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type CredentialStatus, type Stats } from "@/lib/api";
import { cn } from "@/lib/utils";

const URGENT: CredentialStatus[] = [
  "excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90",
];

const PAGE_SIZE = 25;

/** Urgency buckets shown as tiles. A bucket with `statuses` filters the associates table when clicked. */
interface Tile {
  label: string;
  value: number;
  accent: string;
  statuses?: CredentialStatus[];
}

function tiles(stats: Stats): Tile[] {
  const s = stats.by_status;
  return [
    { label: "Excluded", value: s.excluded, accent: "border-l-red-500", statuses: ["excluded"] },
    { label: "Expired", value: s.expired, accent: "border-l-red-500", statuses: ["expired"] },
    { label: "Verification failed", value: s.verification_failed, accent: "border-l-red-500", statuses: ["verification_failed"] },
    { label: "Expiring in 30 days", value: s.expiring_30, accent: "border-l-orange-500", statuses: ["expiring_30"] },
    {
      label: "Expiring in 31–90 days",
      value: s.expiring_60 + s.expiring_90,
      accent: "border-l-yellow-400",
      statuses: ["expiring_60", "expiring_90"],
    },
    { label: "Valid", value: s.valid, accent: "border-l-green-500", statuses: ["valid"] },
    { label: "Not yet verified", value: stats.unverified, accent: "border-l-gray-400" },
  ];
}

function TileCard({ tile, selected, onSelect }: { tile: Tile; selected: boolean; onSelect?: () => void }) {
  const body = (
    <Card className={cn("h-full border-l-4", tile.accent, selected && "ring-2 ring-ring")}>
      <CardContent>
        <div className="text-2xl font-semibold tabular-nums">{tile.value.toLocaleString()}</div>
        <div className="text-xs text-muted-foreground">{tile.label}</div>
      </CardContent>
    </Card>
  );
  if (!onSelect) return body;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      title={selected ? "Show all associates" : `Show associates with a credential in "${tile.label}"`}
      className="rounded-xl text-left transition-shadow hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
    >
      {body}
    </button>
  );
}

export default function Dashboard() {
  const { scope, filters } = useScope();
  const queryClient = useQueryClient();
  const [bucket, setBucket] = useState<Tile | null>(null);
  const [sort, setSort] = useState<AssociateSort>("urgency");

  // Paging resets to the first page whenever the scope, bucket or sort changes.
  const listKey = JSON.stringify([scope, bucket?.label, sort]);
  const [paging, setPaging] = useState({ key: listKey, offset: 0 });
  const offset = paging.key === listKey ? paging.offset : 0;
  const goTo = (next: number) => setPaging({ key: listKey, offset: next });

  const stats = useQuery({ queryKey: ["stats", scope], queryFn: () => api.stats(scope) });
  const urgent = useQuery({
    queryKey: ["credentials", scope, "urgent"],
    queryFn: () => api.credentials({ ...scope, status: URGENT, limit: 50 }),
  });
  const associates = useQuery({
    queryKey: ["associates", scope, bucket?.statuses, sort, offset],
    queryFn: () => api.associatesPage({ ...scope, status: bucket?.statuses, sort, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData,
  });
  const verifyAll = useMutation({
    mutationFn: () => api.verifyAll(scope),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const error = stats.error ?? urgent.error ?? associates.error ?? verifyAll.error;
  const urgentTotal = stats.data ? URGENT.reduce((n, s) => n + stats.data.by_status[s], 0) : 0;
  const total = associates.data?.total ?? 0;

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

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        {stats.data &&
          tiles(stats.data).map((tile) => {
            const selected = bucket?.label === tile.label;
            return (
              <TileCard
                key={tile.label}
                tile={tile}
                selected={selected}
                onSelect={tile.statuses && (() => setBucket(selected ? null : tile))}
              />
            );
          })}
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
            urgent.data.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Nothing needs attention 🎉</p>
            ) : (
              <CredentialTable credentials={urgent.data} />
            )
          ) : (
            !error && <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            Associates
            {bucket && (
              <Button variant="outline" size="xs" onClick={() => setBucket(null)} aria-label={`Clear filter: ${bucket.label}`}>
                {bucket.label}
                <X aria-hidden />
              </Button>
            )}
          </CardTitle>
          <CardDescription>
            {bucket
              ? `Associates with at least one credential in "${bucket.label}"`
              : "Everyone in scope, most urgent first. Click a tile above to filter."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {associates.data ? (
            <div className={cn(associates.isPlaceholderData && "opacity-60")}>
              <AssociateTable associates={associates.data.items} sort={sort} onSortChange={setSort} />
              {total > 0 && (
                <div className="flex items-center justify-end gap-3 pt-3 text-sm text-muted-foreground">
                  <span className="tabular-nums">
                    {(offset + 1).toLocaleString()}–{Math.min(offset + PAGE_SIZE, total).toLocaleString()} of{" "}
                    {total.toLocaleString()}
                  </span>
                  <Button variant="outline" size="sm" onClick={() => goTo(offset - PAGE_SIZE)} disabled={offset === 0}>
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goTo(offset + PAGE_SIZE)}
                    disabled={offset + PAGE_SIZE >= total}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          ) : (
            !error && <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
