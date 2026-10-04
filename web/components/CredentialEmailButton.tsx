"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Mail } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import type { Credential } from "@/lib/api";
import { api } from "@/lib/api";

export function CredentialEmailButton({ credential }: { credential: Credential }) {
  const queryClient = useQueryClient();
  const contact = useMutation({
    mutationFn: () => api.emailCredentialContact(credential.id),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["credentials"] });
      const action = result.kind === "initial" ? "Notification" : "Follow-up";
      toast.success(result.channel === "email" ? `${action} emailed` : `${action} recorded in the outbox`, {
        description: `For ${result.sent_to}`,
      });
    },
    onError: (error) => {
      toast.error("Could not send credential email", {
        description: error instanceof Error ? error.message : "The request failed.",
      });
    },
  });

  if (!["expiring_90", "expiring_60", "expiring_30", "expired"].includes(credential.status)) return null;

  const label = credential.email_contacted ? "Follow up" : "Email";
  return (
    <Button
      size="sm"
      variant="outline"
      disabled={contact.isPending}
      aria-label={`${label} manager about ${credential.credential_type} for ${credential.associate_name}`}
      title={
        credential.last_email_contact_channel === "outbox"
          ? "The previous notification is recorded in the outbox."
          : undefined
      }
      onClick={() => contact.mutate()}
    >
      <Mail aria-hidden />
      {contact.isPending ? "Sending…" : label}
    </Button>
  );
}
