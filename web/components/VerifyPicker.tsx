"use client";

import { Search } from "lucide-react";
import { useEffect, useRef } from "react";

import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Credential } from "@/lib/api";
import { cn } from "@/lib/utils";

export type Show = "unverified" | "all";

function Choice({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <Button type="button" size="sm" variant={pressed ? "default" : "ghost"} aria-pressed={pressed} onClick={onClick}>
      {children}
    </Button>
  );
}

/** Search and filters over the hand-checked credentials, and the list to pick one from. */
export function VerifyPicker({
  credentials,
  listed,
  currentId,
  onPick,
  search,
  onSearch,
  source,
  onSource,
  show,
  onShow,
}: {
  credentials: Credential[]; // every hand-checked credential in scope, for the source choices
  listed: Credential[]; // the ones matching the search and filters
  currentId: number | null;
  onPick: (id: number) => void;
  search: string;
  onSearch: (value: string) => void;
  source: string | null;
  onSource: (value: string | null) => void;
  show: Show;
  onShow: (value: Show) => void;
}) {
  const sources = [...new Set(credentials.map((c) => c.issuing_source))].sort();
  // Keep the chosen person in sight inside the list, for a pick that came from a link on another page.
  const list = useRef<HTMLUListElement>(null);
  useEffect(() => {
    const row = list.current?.querySelector<HTMLElement>("[aria-current='true']");
    if (row && list.current) list.current.scrollTop = row.offsetTop - list.current.offsetTop;
  }, [currentId, listed.length]);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Who to verify</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-52 flex-1">
            <Search aria-hidden className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              aria-label="Search by name"
              placeholder="Search by name"
              value={search}
              onChange={(event) => onSearch(event.target.value)}
              className="h-9 w-full rounded-lg border border-input bg-transparent pr-3 pl-9 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            />
          </div>
          <div role="group" aria-label="Source" className="flex flex-wrap items-center gap-1 rounded-lg border p-0.5">
            <Choice pressed={source === null} onClick={() => onSource(null)}>
              All sources
            </Choice>
            {sources.map((s) => (
              <Choice key={s} pressed={source === s} onClick={() => onSource(s)}>
                {s}
              </Choice>
            ))}
          </div>
          <div role="group" aria-label="Show" className="flex items-center gap-1 rounded-lg border p-0.5">
            <Choice pressed={show === "unverified"} onClick={() => onShow("unverified")}>
              Still to verify
            </Choice>
            <Choice pressed={show === "all"} onClick={() => onShow("all")}>
              All
            </Choice>
          </div>
        </div>
        <p className="text-xs text-muted-foreground tabular-nums">{listed.length} shown</p>
        {listed.length > 0 && (
          <ul ref={list} aria-label="People to verify" className="relative max-h-64 divide-y overflow-y-auto rounded-lg border">
            {listed.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  aria-current={c.id === currentId}
                  onClick={() => onPick(c.id)}
                  className={cn(
                    "flex w-full flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-left text-sm hover:bg-muted/60",
                    c.id === currentId && "bg-muted font-medium",
                  )}
                >
                  <span className="min-w-40 flex-1">{c.associate_name}</span>
                  <span className="text-xs font-normal text-muted-foreground">
                    {c.credential_type} · {c.issuing_source}
                  </span>
                  <StatusBadge status={c.status} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
