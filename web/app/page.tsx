"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AssociateTable, type AssociateSort } from "@/components/AssociateTable";
import { CredentialEmailButton } from "@/components/CredentialEmailButton";
import { CredentialTable } from "@/components/CredentialTable";
import { ExpiryTimelineChart } from "@/components/ExpiryTimelineChart";
import { ManagerProgressTable, teamCounts } from "@/components/ManagerProgressTable";
import { useHrScope, useRole } from "@/components/Providers";
import { useScope } from "@/components/ScopeFilters";
import { StatusBreakdownChart } from "@/components/StatusBreakdownChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type CredentialStatus, type Scope, type Stats, type VerifyAllResult } from "@/lib/api";
import { managerName } from "@/lib/format";
import { cn } from "@/lib/utils";

const URGENT: CredentialStatus[] = [
  "excluded", "expired", "verification_failed", "expiring_30", "expiring_60", "expiring_90", "unverified",
];

// HR's list is narrower: things that are wrong now or about to be, not everything still to do.
const PROBLEMS: CredentialStatus[] = ["excluded", "expired", "verification_failed", "expiring_30"];

const PAGE_SIZE = 25;
const TILE_COUNT = 7;

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
        <div className="text-3xl font-semibold tracking-tight tabular-nums">{tile.value.toLocaleString()}</div>
        <div className="text-xs text-muted-foreground">{tile.label}</div>
      </CardContent>
    </Card>
  );
  if (!onSelect) {
    return (
      <div className="h-full cursor-default" title={tile.statuses ? undefined : "Not filterable"}>
        {body}
      </div>
    );
  }
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

/** Placeholder at the same height as a loaded tile. */
function TileSkeleton() {
  return (
    <Card className="h-full border-l-4 border-l-muted" aria-hidden>
      <CardContent className="space-y-2">
        <Skeleton className="h-9 w-16" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}

/** Loading, empty and error text inside a dashboard card, styled the same everywhere. */
function SectionMessage({ children, className, role }: { children: React.ReactNode; className?: string; role?: "status" }) {
  return (
    <p role={role} className={cn("py-8 text-center text-sm text-muted-foreground", className)}>
      {children}
    </p>
  );
}

function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {children}
    </p>
  );
}

/**
 * Verify all result. ARRT is skipped (it needs a person for its robot check); ARDMS, NMTCB and Michigan are
 * looked up automatically, and any of those the lookup could not settle are left for a person too.
 */
function VerifyAllMessage({ result }: { result: VerifyAllResult }) {
  const { checked, skipped_manual: manual } = result;
  const verified = result.by_result.verified ?? 0;
  const unsettled = checked - verified;
  if (manual === 0 && unsettled === 0) return <>Checked {checked.toLocaleString()} credentials</>;
  return (
    <>
      {checked > 0 && (
        <>
          Checked {checked.toLocaleString()} automatically: {verified.toLocaleString()} verified
          {unsettled > 0 && <>, {unsettled.toLocaleString()} {unsettled === 1 ? "needs" : "need"} a person</>} ·{" "}
        </>
      )}
      {manual > 0 && <>{manual.toLocaleString()} to check by hand · </>}
      <Link href="/verify" className="font-medium text-foreground hover:underline">
        Open Verify
      </Link>
    </>
  );
}

/** "26–50 of 151" with Previous and Next, under a paged table. Nothing when the table is empty. */
function Pager({ offset, total, onGo }: { offset: number; total: number; onGo: (offset: number) => void }) {
  if (total === 0) return null;
  return (
    <div className="flex items-center justify-end gap-3 pt-3 text-sm text-muted-foreground">
      <span className="tabular-nums">
        {(offset + 1).toLocaleString()}–{Math.min(offset + PAGE_SIZE, total).toLocaleString()} of {total.toLocaleString()}
      </span>
      <Button variant="outline" size="sm" onClick={() => onGo(offset - PAGE_SIZE)} disabled={offset === 0}>
        Previous
      </Button>
      <Button variant="outline" size="sm" onClick={() => onGo(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total}>
        Next
      </Button>
    </div>
  );
}

/** HR's four tiles. Together they add up to every credential in scope. */
function summaryTiles(stats: Stats): Tile[] {
  const counts = teamCounts(stats);
  // `statuses` is set so the tiles don't carry the "Not filterable" hint; they are not clickable here.
  return [
    { label: "Problems", value: counts.problems, accent: "border-l-red-500", statuses: [] },
    { label: "Expiring within 90 days", value: counts.expiring, accent: "border-l-yellow-400", statuses: [] },
    { label: "Valid", value: counts.valid, accent: "border-l-green-500", statuses: [] },
    { label: "Not yet verified", value: counts.unverified, accent: "border-l-gray-400", statuses: [] },
  ];
}

/** The people on one manager's team, most urgent first. Shown to HR once a manager is chosen. */
function TeamCard({ scope }: { scope: Scope }) {
  const [sort, setSort] = useState<AssociateSort>("urgency");
  const listKey = JSON.stringify([scope, sort]);
  const [paging, setPaging] = useState({ key: listKey, offset: 0 });
  const offset = paging.key === listKey ? paging.offset : 0;
  const associates = useQuery({
    queryKey: ["associates", scope, undefined, sort, offset],
    queryFn: () => api.associatesPage({ ...scope, sort, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData,
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>{scope.manager ? `${managerName(scope.manager)}'s team` : "Team"}</CardTitle>
        <CardDescription>Everyone on this team, most urgent first.</CardDescription>
      </CardHeader>
      <CardContent>
        {associates.data ? (
          <div className={cn(associates.isPlaceholderData && "opacity-60")} aria-busy={associates.isFetching}>
            <AssociateTable associates={associates.data.items} sort={sort} onSortChange={setSort} />
            <Pager offset={offset} total={associates.data.total} onGo={(next) => setPaging({ key: listKey, offset: next })} />
          </div>
        ) : associates.error ? (
          <SectionMessage>Couldn&apos;t load associates.</SectionMessage>
        ) : (
          <SectionMessage role="status">Loading…</SectionMessage>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * HR oversees; managers do the verifying. So HR's dashboard answers "which teams need a look?":
 * a few totals, each manager's progress, and the credentials that are actually a problem.
 */
function HrDashboard() {
  const { scope, filters } = useScope();
  const [, setPicked] = useHrScope();
  const queryClient = useQueryClient();
  const stats = useQuery({ queryKey: ["stats", scope], queryFn: () => api.stats(scope) });
  const managers = useQuery({
    queryKey: ["stats", "managers", scope.department, scope.facility],
    queryFn: () => api.managerStats(scope),
  });
  const problems = useQuery({
    queryKey: ["credentials", scope, "problems"],
    queryFn: () => api.credentials({ ...scope, status: PROBLEMS, limit: 50 }),
  });
  const verifyAll = useMutation({
    mutationFn: () => api.verifyAll(scope),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const error = stats.error ?? managers.error ?? problems.error;
  const problemTotal = stats.data ? PROBLEMS.reduce((n, s) => n + stats.data.by_status[s], 0) : 0;
  const pickManager = (manager: string | undefined) => setPicked((p) => ({ ...p, manager }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-full min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          {filters}
        </div>
        <div className="flex items-center gap-3">
          {verifyAll.data && (
            <p className="text-sm text-muted-foreground" role="status">
              <VerifyAllMessage result={verifyAll.data} />
            </p>
          )}
          <Button onClick={() => verifyAll.mutate()} disabled={verifyAll.isPending}>
            <RefreshCw className={verifyAll.isPending ? "animate-spin" : undefined} aria-hidden />
            {verifyAll.isPending ? "Verifying…" : "Verify all"}
          </Button>
        </div>
      </div>

      {error && (
        <ErrorBanner>Could not reach the API ({error.message}). Is the backend running on port 8000?</ErrorBanner>
      )}
      {verifyAll.error && <ErrorBanner>Verify all failed ({verifyAll.error.message}).</ErrorBanner>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.isLoading && Array.from({ length: 4 }, (_, i) => <TileSkeleton key={i} />)}
        {stats.error && <SectionMessage className="col-span-full py-4">Couldn&apos;t load counts.</SectionMessage>}
        {stats.data && summaryTiles(stats.data).map((tile) => <TileCard key={tile.label} tile={tile} selected={false} />)}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            Progress by manager
            {scope.manager && (
              <Button variant="outline" size="xs" onClick={() => pickManager(undefined)}>
                Show all managers
                <X aria-hidden />
              </Button>
            )}
          </CardTitle>
          <CardDescription>
            Teams that most need a look come first. Choose a manager to see only their team on this page.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {managers.data ? (
            managers.data.length === 0 ? (
              <SectionMessage>No teams match these filters.</SectionMessage>
            ) : (
              // With many managers the table scrolls inside the card, so the problems list stays within reach.
              <div className="max-h-[26rem] overflow-y-auto">
                <ManagerProgressTable rows={managers.data} selected={scope.manager} onSelect={pickManager} />
              </div>
            )
          ) : managers.error ? (
            <SectionMessage>Couldn&apos;t load the teams.</SectionMessage>
          ) : (
            <SectionMessage role="status">Loading…</SectionMessage>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Problems and expiring within 30 days</CardTitle>
          <CardDescription>
            {stats.isLoading && <Skeleton className="h-5 w-72 max-w-full" />}
            {stats.data &&
              `${problemTotal.toLocaleString()} ${problemTotal === 1 ? "credential is" : "credentials are"} excluded, expired, failed a check or ` +
                "expire within 30 days" +
                (problemTotal > 50 ? "; showing the 50 most urgent" : "")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {problems.data ? (
            problems.data.length === 0 ? (
              <SectionMessage>No problems right now.</SectionMessage>
            ) : (
              <div className="[&_td:nth-child(1)_div]:whitespace-normal [&_td:nth-child(2)]:whitespace-normal [&_td:nth-child(4)]:whitespace-normal [&_td:nth-child(6)]:whitespace-normal">
                <CredentialTable
                  credentials={problems.data}
                  action={(credential) => <CredentialEmailButton credential={credential} />}
                />
              </div>
            )
          ) : problems.error ? (
            <SectionMessage>Couldn&apos;t load credentials.</SectionMessage>
          ) : (
            <SectionMessage role="status">Loading…</SectionMessage>
          )}
        </CardContent>
      </Card>

      {scope.manager && <TeamCard scope={scope} />}

      <div className="grid gap-4 min-[72rem]:grid-cols-2">
        <StatusBreakdownChart stats={stats.data} isLoading={stats.isLoading} error={stats.error} />
        <ExpiryTimelineChart stats={stats.data} isLoading={stats.isLoading} error={stats.error} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { role } = useRole();
  return role === "hr" ? <HrDashboard /> : <ManagerDashboard />;
}

function ManagerDashboard() {
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
  const error = stats.error ?? urgent.error ?? associates.error;
  const urgentTotal = stats.data ? URGENT.reduce((n, s) => n + stats.data.by_status[s], 0) : 0;
  const total = associates.data?.total ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-full min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          {filters}
        </div>
        <div className="flex items-center gap-3">
          {verifyAll.data && (
            <p className="text-sm text-muted-foreground" role="status">
              <VerifyAllMessage result={verifyAll.data} />
            </p>
          )}
          <Button onClick={() => verifyAll.mutate()} disabled={verifyAll.isPending}>
            <RefreshCw className={verifyAll.isPending ? "animate-spin" : undefined} aria-hidden />
            {verifyAll.isPending ? "Verifying…" : "Verify all"}
          </Button>
        </div>
      </div>

      {error && (
        <ErrorBanner>Could not reach the API ({error.message}). Is the backend running on port 8000?</ErrorBanner>
      )}
      {verifyAll.error && <ErrorBanner>Verify all failed ({verifyAll.error.message}).</ErrorBanner>}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
        {stats.isLoading && Array.from({ length: TILE_COUNT }, (_, i) => <TileSkeleton key={i} />)}
        {stats.error && <SectionMessage className="col-span-full py-4">Couldn&apos;t load counts.</SectionMessage>}
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

      {/* Side by side only from 72rem: below that each card is too narrow for the status chart's label column. */}
      <div className="grid gap-4 min-[72rem]:grid-cols-2">
        <StatusBreakdownChart stats={stats.data} isLoading={stats.isLoading} error={stats.error} />
        <ExpiryTimelineChart stats={stats.data} isLoading={stats.isLoading} error={stats.error} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Needs attention</CardTitle>
          <CardDescription>
            {stats.isLoading && <Skeleton className="h-5 w-72 max-w-full" />}
            {stats.data &&
              `${stats.data.associates.toLocaleString()} associates · ${urgentTotal.toLocaleString()} credentials need attention` +
                (urgentTotal > 50 ? ", showing the 50 most urgent" : "")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {urgent.data ? (
            urgent.data.length === 0 ? (
              <SectionMessage>Nothing needs attention 🎉</SectionMessage>
            ) : (
              // Same wrapping as the Credentials page: HR's list (BLS rows with "American Heart Association", long
              // facility names) is wider than the card even at 100%, so let the associate's department line and the
              // Credential, Expires and Last verified cells (2nd, 4th, 6th) wrap when space runs out; Evidence then fits.
              <div className="[&_td:nth-child(1)_div]:whitespace-normal [&_td:nth-child(2)]:whitespace-normal [&_td:nth-child(4)]:whitespace-normal [&_td:nth-child(6)]:whitespace-normal">
                <CredentialTable
                  credentials={urgent.data}
                  action={(credential) => <CredentialEmailButton credential={credential} />}
                />
              </div>
            )
          ) : urgent.error ? (
            <SectionMessage>Couldn&apos;t load credentials.</SectionMessage>
          ) : (
            <SectionMessage role="status">Loading…</SectionMessage>
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
            <div className={cn(associates.isPlaceholderData && "opacity-60")} aria-busy={associates.isFetching}>
              <AssociateTable associates={associates.data.items} sort={sort} onSortChange={setSort} />
              <Pager offset={offset} total={total} onGo={goTo} />
            </div>
          ) : associates.error ? (
            <SectionMessage>Couldn&apos;t load associates.</SectionMessage>
          ) : (
            <SectionMessage role="status">Loading…</SectionMessage>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
