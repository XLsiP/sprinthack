"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BellRing } from "lucide-react";
import { toast } from "sonner";

import { THRESHOLD } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type AlertRunResult, type AlertThreshold } from "@/lib/api";

function describe(result: AlertRunResult): string {
  const parts = (Object.entries(result.by_threshold) as [AlertThreshold, number][]).map(
    ([threshold, count]) => `${count.toLocaleString()} × ${THRESHOLD[threshold].label}`,
  );
  const emailed = result.by_channel?.email ?? 0;
  const delivery = emailed > 0 ? ` ${emailed.toLocaleString()} emailed, the rest kept in the outbox.` : " Recorded in the outbox.";
  return `Sent to managers and HR: ${parts.join(", ")}.${delivery}`;
}

/** Demo action: run the alert sweep now instead of waiting for the daily job. */
export function AlertRunButton() {
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: api.runAlerts,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries(); // the sweep also refreshes stored statuses
      if (result.sent === 0) {
        toast.info("No new alerts", { description: "Every due threshold was already sent once." });
      } else {
        const label = `${result.sent.toLocaleString()} new ${result.sent === 1 ? "alert" : "alerts"} sent`;
        toast.success(label, { description: describe(result) });
      }
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 503) {
        toast.warning("Alert sweep is not configured", { description: "Set HR_EMAIL in the API environment, then try again." });
      } else {
        toast.error("Alert sweep did not run", { description: "Could not reach the API. Nothing was sent." });
      }
    },
  });

  return (
    <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending}>
      <BellRing className={run.isPending ? "animate-pulse" : undefined} aria-hidden />
      {run.isPending ? "Sending…" : "Run alert sweep"}
    </Button>
  );
}
