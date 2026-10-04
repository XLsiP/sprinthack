"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, ExternalLink, ScanText, SkipForward } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useDemoManager, useRole } from "@/components/Providers";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Credential, type ManualVerification } from "@/lib/api";
import { type HelperResult, listenForHelper } from "@/lib/helper";
import { lookupLink } from "@/lib/lookup";
import { cn } from "@/lib/utils";

const FIELD =
  "h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function Recorder({ credential, onDone, onSkip }: { credential: Credential; onDone: () => void; onSkip: () => void }) {
  const [number, setNumber] = useState("");
  const [expires, setExpires] = useState("");
  const [note, setNote] = useState("");
  const [read, setRead] = useState<HelperResult | null>(null);
  // The helper extension reads the result off the lookup page; fill the form with it for the person to check.
  useEffect(
    () =>
      listenForHelper(credential.id, (result) => {
        setRead(result);
        if (result.expires) setExpires(result.expires);
        if (result.number) setNumber(result.number);
        if (result.summary) setNote(`${result.source} page showed: ${result.summary}`.slice(0, 500));
      }),
    [credential.id],
  );
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
          {read && (
            <div
              role="status"
              className={cn("flex gap-2 rounded-lg border bg-muted/50 p-3 text-sm", read.mismatch && "border-orange-300 bg-orange-50")}
            >
              <ScanText aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <p>
                {read.none
                  ? `The ${read.source} page showed no match. Try another spelling there first; if there is still none, choose "Not found at source".`
                  : read.expires
                    ? `Filled in from the ${read.source} page. Check it against the page, then save.`
                    : `The ${read.source} page showed no expiry date. Enter it yourself if there is one.`}
                {read.mismatch && (
                  <span className="font-medium">
                    {" "}
                    The name on that page did not look like {credential.associate_name}; make sure it is the right person.
                  </span>
                )}
                {read.hint && <span className="text-muted-foreground"> {read.hint}</span>}
              </p>
            </div>
          )}
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
