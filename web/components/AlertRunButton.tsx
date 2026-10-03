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

/** Title and description for a failed sweep; a 503 means HR_EMAIL is not set in the API environment. */
function failure(error: Error): { title: string; description: string } {
  if (error instanceof ApiError && error.status === 503) {
    return { title: "Alert sweep is not configured", description: "Set HR_EMAIL in the API environment, then try again." };
  }
  if (error instanceof ApiError) {
    return { title: "Alert sweep did not run", description: `The API returned an error (${error.message}). Nothing was sent.` };
  }
  return { title: "Alert sweep did not run", description: "Could not reach the API. Nothing was sent." };
}

/**
 * Demo action: run the alert sweep now instead of waiting for the daily job. Results show as toasts; `onError` and
 * `onSuccess` let the page also keep a failure on screen until the next successful run.
 */
export function AlertRunButton({ onError, onSuccess }: { onError?: (message: string) => void; onSuccess?: () => void }) {
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: api.runAlerts,
    onSuccess: async (result) => {
      onSuccess?.();
      await queryClient.invalidateQueries(); // the sweep also refreshes stored statuses
      if (result.sent === 0) {
        toast.info("No new alerts", { description: "Every due threshold was already sent once." });
      } else {
        const label = `${result.sent.toLocaleString()} new ${result.sent === 1 ? "alert" : "alerts"} sent`;
        toast.success(label, { description: describe(result) });
      }
    },
    onError: (error) => {
      const { title, description } = failure(error);
      const notConfigured = error instanceof ApiError && error.status === 503;
      (notConfigured ? toast.warning : toast.error)(title, { description });
      onError?.(`${title}. ${description}`);
    },
  });

  return (
    <Button onClick={() => run.mutate()} disabled={run.isPending}>
      <BellRing className={run.isPending ? "animate-pulse" : undefined} aria-hidden />
      {run.isPending ? "Sending…" : "Run alert sweep"}
    </Button>
  );
}
