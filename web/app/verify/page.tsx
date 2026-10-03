"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, ExternalLink, SkipForward } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { useDemoManager, useRole } from "@/components/Providers";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Credential, type ManualVerification } from "@/lib/api";

const FIELD =
  "h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

/** The lookup page for a credential, with the name filled in where the source's page accepts it. */
function lookupLink(c: Credential): string | null {
  if (!c.lookup_url) return null;
  if (c.issuing_source === "NMTCB") {
    const parts = c.associate_name.split(" ");
    const query = new URLSearchParams({ LastName: parts[parts.length - 1], FirstName: parts.slice(0, -1).join(" ") });
    return `https://www.nmtcb.org/verification/results?${query}`;
  }
  return c.lookup_url;
}

function Recorder({ credential, onDone, onSkip }: { credential: Credential; onDone: () => void; onSkip: () => void }) {
  const [number, setNumber] = useState("");
  const [expires, setExpires] = useState("");
  const [note, setNote] = useState("");
  const save = useMutation({
    mutationFn: (body: ManualVerification) => api.recordManualVerification(credential.id, body),
    onSuccess: (verification) => {
      if (verification.result === "verified") {
        toast.success(`${credential.associate_name}: ${credential.credential_type} recorded`, {
          description: `Expires ${expires}. Expiry tracking and alerts now apply.`,
        });
      } else {
        toast.warning(`${credential.associate_name}: recorded as not found`, {
          description: "It now shows as verification failed until someone follows up.",
        });
      }
      onDone();
    },
    onError: (error) => toast.error("Could not save", { description: error.message }),
  });
  const link = lookupLink(credential);

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Link href={`/associates/${credential.associate_id}`} className="hover:underline">
            {credential.associate_name}
          </Link>
        </CardTitle>
        <CardDescription>
          {credential.credential_type} · checked by hand at {credential.issuing_source}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <p className="text-sm font-medium">1. Look them up</p>
          {link ? (
            <a href={link} target="_blank" rel="noreferrer" className={buttonVariants({ variant: "outline" })}>
              <ExternalLink aria-hidden />
              Open {credential.issuing_source} lookup
            </a>
          ) : (
            <p className="text-sm text-muted-foreground">No lookup page is on file for {credential.issuing_source}.</p>
          )}
        </div>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate({ result: "verified", number: number || undefined, expires_date: expires, note: note || undefined });
          }}
        >
          <p className="text-sm font-medium">2. Record what it shows</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span>Credential or ID number</span>
              <input className={FIELD} value={number} onChange={(e) => setNumber(e.target.value)} maxLength={64} autoComplete="off" />
            </label>
            <label className="space-y-1 text-sm">
              <span>Expires on</span>
              <input className={FIELD} type="date" required value={expires} onChange={(e) => setExpires(e.target.value)} />
            </label>
          </div>
          <label className="block space-y-1 text-sm">
            <span>Note (optional)</span>
            <input className={FIELD} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} autoComplete="off" />
          </label>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button type="submit" disabled={save.isPending}>
              <CircleCheck aria-hidden />
              {save.isPending ? "Saving…" : "Save and next"}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={save.isPending}
              onClick={() => save.mutate({ result: "not_found", note: note || undefined })}
            >
              Not found at source
            </Button>
            <Button type="button" variant="ghost" disabled={save.isPending} onClick={onSkip}>
              <SkipForward aria-hidden />
              Skip for now
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export default function VerifyQueuePage() {
  const { role } = useRole();
  const { manager, team } = useDemoManager();
  const queryClient = useQueryClient();
  const scope = role === "manager" ? { manager } : {};
  const queue = useQuery({
    queryKey: ["credentials", "verify-queue", scope],
    queryFn: () => api.allCredentials({ ...scope, status: ["unverified"] }),
  });
  const [skipped, setSkipped] = useState<number[]>([]);

  // Hand-verified credentials only; the app checks the others itself.
  const waiting = (queue.data ?? []).filter((c) => c.verify_method === "manual");
  const current = waiting.find((c) => !skipped.includes(c.id)) ?? waiting[0];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Verify credentials</h1>
        <p className="text-sm text-muted-foreground">
          {role === "manager" ? `Your team: ${team}. ` : "All teams. "}
          These sources block automated lookups, so a person checks each one. Once the expiry date is recorded, the
          app tracks it and sends the alerts.
        </p>
      </div>

      {queue.error && (
        <p role="alert" className="text-sm text-red-800">
          Could not load the queue ({queue.error.message}).
        </p>
      )}
      {queue.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}

      {queue.data && (
        <p className="text-sm tabular-nums" role="status">
          <span className="font-medium">{waiting.length}</span> left to verify
        </p>
      )}

      {queue.data && !current && (
        <Card>
          <CardContent>
            <p className="py-8 text-center text-sm text-muted-foreground">
              Nothing left to verify by hand. New people and renewals will appear here.
            </p>
          </CardContent>
        </Card>
      )}

      {current && (
        <Recorder
          key={current.id}
          credential={current}
          onDone={() => queryClient.invalidateQueries()}
          onSkip={() => setSkipped((ids) => (ids.includes(current.id) ? [] : [...ids, current.id]))}
        />
      )}
    </div>
  );
}
