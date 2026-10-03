"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, ApiError, type DailyRunResult } from "@/lib/api";

function describe(result: DailyRunResult): string {
  const checked = `${result.checked.toLocaleString()} credentials re-verified`;
  if (result.alerts === null) return `${checked}. Alerts were skipped: ${result.alerts_skipped ?? "not configured"}.`;
  const sent = result.alerts.sent;
  return `${checked}, ${sent.toLocaleString()} new ${sent === 1 ? "alert" : "alerts"} sent.`;
}

/** Admin action for the demo: run the scheduled daily re-verification and alert sweep right now. */
export function DailyRunButton() {
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: api.runDailyJob,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries();
      const notify = result.alerts === null ? toast.warning : toast.success;
      notify("Daily check complete", { description: describe(result) });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        toast.warning("Daily check already running", { description: "Wait for the current run to finish." });
      } else {
        toast.error("Daily check did not run", { description: "Could not reach the API. Nothing was changed." });
      }
    },
  });

  return (
    <Button size="sm" variant="outline" onClick={() => run.mutate()} disabled={run.isPending}>
      <CalendarClock className={run.isPending ? "animate-pulse" : undefined} aria-hidden />
      {run.isPending ? "Running…" : "Run daily check"}
    </Button>
  );
}
