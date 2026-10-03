"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AXIS_TICK, ChartCard, ChartTooltipBox, GRID_STROKE } from "@/components/ChartCard";
import { statusFill, UNVERIFIED_FILL } from "@/components/StatusBadge";
import type { Stats } from "@/lib/api";

interface Row {
  label: string;
  count: number;
  fill: string;
}

/** Same buckets and labels as the dashboard tiles. */
function rows(stats: Stats): Row[] {
  const s = stats.by_status;
  return [
    { label: "Excluded", count: s.excluded, fill: statusFill("excluded") },
    { label: "Expired", count: s.expired, fill: statusFill("expired") },
    { label: "Verification failed", count: s.verification_failed, fill: statusFill("verification_failed") },
    { label: "Expiring in 30 days", count: s.expiring_30, fill: statusFill("expiring_30") },
    { label: "Expiring in 31–90 days", count: s.expiring_60 + s.expiring_90, fill: statusFill("expiring_90") },
    { label: "Valid", count: s.valid, fill: statusFill("valid") },
  ];
}

/** Credentials in scope by status, as horizontal bars. */
export function StatusBreakdownChart({ stats, isLoading, error }: { stats?: Stats; isLoading: boolean; error: Error | null }) {
  const description = stats
    ? `Counts credentials, not people · ${stats.credentials.toLocaleString()} credentials held by ${stats.associates.toLocaleString()} associates`
    : "Counts credentials, not people";

  return (
    <ChartCard
      title="Credentials by status"
      description={description}
      isLoading={isLoading}
      error={error}
      empty={stats && stats.credentials === 0 ? "No credentials in this scope." : undefined}
      footer={
        stats && (
          // Unverified credentials still have a date-based status, so they overlap the bars rather than adding a bar.
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: UNVERIFIED_FILL }} aria-hidden />
            {stats.unverified.toLocaleString()} of these credentials are not yet verified
          </p>
        )
      }
    >
      {stats && (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows(stats)} layout="vertical" margin={{ top: 0, right: 48, bottom: 16, left: 0 }} barCategoryGap={6}>
            <CartesianGrid horizontal={false} stroke={GRID_STROKE} />
            <XAxis
              type="number"
              allowDecimals={false}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              label={{ value: "Credentials", position: "insideBottom", offset: -12, ...AXIS_TICK }}
            />
            <YAxis type="category" dataKey="label" width={180} tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: "var(--muted)" }}
              content={({ active, payload }) => {
                const row = payload?.[0]?.payload as Row | undefined;
                return active && row ? <ChartTooltipBox label={row.label} value={row.count} /> : null;
              }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {rows(stats).map((row) => (
                <Cell key={row.label} fill={row.fill} />
              ))}
              <LabelList
                dataKey="count"
                position="right"
                className="tabular-nums"
                style={{ fontSize: 12, fill: "var(--foreground)" }}
                formatter={(v) => (typeof v === "number" ? v.toLocaleString() : v)}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
