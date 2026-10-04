"use client";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ManagerStats } from "@/lib/api";
import { managerName } from "@/lib/format";
import { cn } from "@/lib/utils";

/** The counts HR watches for one team. Together they add up to the team's credentials. */
export function teamCounts(row: Pick<ManagerStats, "by_status">) {
  const s = row.by_status;
  return {
    problems: s.excluded + s.expired + s.verification_failed,
    expiring: s.expiring_30 + s.expiring_60 + s.expiring_90,
    valid: s.valid,
    unverified: s.unverified,
  };
}

function Count({ value, tone }: { value: number; tone?: string }) {
  return <span className={cn("tabular-nums", value > 0 ? tone : "text-muted-foreground")}>{value.toLocaleString()}</span>;
}

/** One row per manager: how far their team's verification has got and what needs their attention. */
export function ManagerProgressTable({
  rows,
  selected,
  onSelect,
}: {
  rows: ManagerStats[];
  selected: string | undefined;
  onSelect: (manager: string | undefined) => void;
}) {
  const teams = rows
    .map((row) => {
      const counts = teamCounts(row);
      // Verified and in date: valid, or valid but coming up for renewal.
      const verified = counts.valid + counts.expiring;
      return { ...row, ...counts, verified, share: row.credentials ? verified / row.credentials : 0 };
    })
    // The teams that most need a look first: most problems, then least progress.
    .sort((a, b) => b.problems - a.problems || a.share - b.share || a.manager.localeCompare(b.manager));

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Manager</TableHead>
          <TableHead className="text-right">People</TableHead>
          <TableHead className="w-[28%] min-w-40">Verified</TableHead>
          <TableHead className="text-right">Expiring within 90 days</TableHead>
          <TableHead className="text-right">Problems</TableHead>
          <TableHead className="text-right">Not yet verified</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {teams.map((team) => (
          <TableRow key={team.manager} className={cn(selected === team.manager && "bg-muted")}>
            <TableCell>
              <button
                type="button"
                title={team.manager}
                aria-pressed={selected === team.manager}
                onClick={() => onSelect(selected === team.manager ? undefined : team.manager)}
                className="rounded font-medium hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              >
                {managerName(team.manager)}
              </button>
            </TableCell>
            <TableCell className="text-right tabular-nums">{team.associates.toLocaleString()}</TableCell>
            <TableCell>
              <div className="flex items-center gap-3">
                <div
                  role="progressbar"
                  aria-label={`${managerName(team.manager)}: credentials verified`}
                  aria-valuemin={0}
                  aria-valuemax={team.credentials}
                  aria-valuenow={team.verified}
                  className="h-2 min-w-16 flex-1 overflow-hidden rounded-full bg-muted-foreground/15"
                >
                  <div className="h-full rounded-full bg-green-500" style={{ width: `${Math.round(team.share * 100)}%` }} />
                </div>
                <span className="text-xs whitespace-nowrap text-muted-foreground tabular-nums">
                  {team.verified.toLocaleString()} of {team.credentials.toLocaleString()}
                </span>
              </div>
            </TableCell>
            <TableCell className="text-right">
              <Count value={team.expiring} tone="text-yellow-700" />
            </TableCell>
            <TableCell className="text-right">
              <Count value={team.problems} tone="font-medium text-red-700" />
            </TableCell>
            <TableCell className="text-right">
              <Count value={team.unverified} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
