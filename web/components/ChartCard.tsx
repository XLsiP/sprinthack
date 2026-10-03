import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** Card frame for a dashboard chart, with shared loading, error and empty states at a fixed height. */
export function ChartCard({
  title,
  description,
  isLoading,
  error,
  empty,
  footer,
  children,
}: {
  title: string;
  description: string;
  isLoading: boolean;
  error: Error | null;
  /** Message shown instead of the chart when there is nothing to plot. */
  empty?: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  let body = children;
  if (error) body = <Message>Couldn&apos;t load chart data.</Message>;
  else if (isLoading) body = <Skeleton className="h-full w-full" />;
  else if (empty) body = <Message>{empty}</Message>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-64">{body}</div>
        {!error && !isLoading && !empty && footer}
      </CardContent>
    </Card>
  );
}

function Message({ children }: { children: React.ReactNode }) {
  return <p className="flex h-full items-center justify-center text-sm text-muted-foreground">{children}</p>;
}

/** Tooltip box shared by the dashboard charts. */
export function ChartTooltipBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="font-medium">{label}</div>
      <div className="text-muted-foreground tabular-nums">
        {value.toLocaleString()} {value === 1 ? "credential" : "credentials"}
      </div>
    </div>
  );
}

/** Recessive axis and grid styling shared by the dashboard charts. */
export const AXIS_TICK = { fontSize: 12, fill: "var(--muted-foreground)" } as const;
export const GRID_STROKE = "var(--border)";
