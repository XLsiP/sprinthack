"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AXIS_TICK, ChartCard, ChartTooltipBox, GRID_STROKE } from "@/components/ChartCard";
import { statusFill } from "@/components/StatusBadge";
import type { Stats } from "@/lib/api";

interface Row {
  tick: string;
  range: string;
  count: number;
  fill: string;
}

/** "YYYY-MM-DD" as a local date; `new Date(iso)` would parse it as UTC and can land on the previous day. */
function localDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

const short = (d: Date) => d.toLocaleDateString("en-US", { month: "short", day: "numeric" });

function rows(stats: Stats): Row[] {
  if (stats.timeline.length === 0) return [];
  const today = localDate(stats.timeline[0].start).getTime();
  return stats.timeline.map((week) => {
    const start = localDate(week.start);
    const daysOut = Math.round((start.getTime() - today) / 86_400_000);
    return {
      tick: short(start),
      range: `${short(start)} – ${short(localDate(week.end))}`,
      count: week.count,
      // The API gives one count per week, so a week starting within 30 days takes the more urgent color.
      fill: statusFill(daysOut <= 30 ? "expiring_30" : "expiring_90"),
    };
  });
}

/** Credentials expiring in the next 90 days, one bar per week starting today. */
export function ExpiryTimelineChart({ stats, isLoading, error }: { stats?: Stats; isLoading: boolean; error: Error | null }) {
  const data = stats ? rows(stats) : [];
  const empty = stats && data.every((row) => row.count === 0) ? "No credentials expire in the next 90 days." : undefined;

  return (
    <ChartCard
      title="Credentials expiring in the next 90 days"
      description="Counts credentials, not people · per week, starting today"
      isLoading={isLoading}
      error={error}
      empty={empty}
      footer={
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          <Legend fill={statusFill("expiring_30")} label="Week starts within 30 days" />
          <Legend fill={statusFill("expiring_90")} label="31–90 days" />
        </div>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke={GRID_STROKE} />
          <XAxis dataKey="tick" tick={AXIS_TICK} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis
            allowDecimals={false}
            width={48}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            label={{ value: "Credentials", angle: -90, position: "insideLeft", ...AXIS_TICK, style: { textAnchor: "middle" } }}
          />
          <Tooltip
            cursor={{ fill: "var(--muted)" }}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as Row | undefined;
              return active && row ? <ChartTooltipBox label={row.range} value={row.count} /> : null;
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((row) => (
              <Cell key={row.tick} fill={row.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function Legend({ fill, label }: { fill: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className="size-2.5 shrink-0 rounded-full" style={{ background: fill }} aria-hidden />
      {label}
    </span>
  );
}
