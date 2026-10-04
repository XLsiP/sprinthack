"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Ban, Download, ExternalLink, LoaderCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { MockBadge, ResultBadge, StatusBadge, UnverifiedBadge } from "@/components/StatusBadge";
import { buttonVariants, Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { verificationFeedback } from "@/components/VerifyFeedback";
import { api, type Credential, evidenceUrl, type VerificationResult } from "@/lib/api";
import { lookupLink } from "@/lib/lookup";
import { checkedAt } from "@/lib/format";
import { cn } from "@/lib/utils";

// Internal flags: `mock` is shown as the MOCK badge, `seeded` marks demo seed data,
// `outcome_source` says how a mock picked its result.
const HIDDEN_DETAILS = new Set(["mock", "seeded", "outcome_source"]);

/** Keys a manager should not see: internal flags and server file paths such as `csv_path`. */
function isInternal(key: string, result: VerificationResult): boolean {
  if (HIDDEN_DETAILS.has(key) || /(^|_)path$/.test(key)) return true;
  // On a failed check, `reason` is raw exception text; the drawer shows a friendly message instead.
  return result === "error" && key === "reason";
}

/** `source_status` → "Source status"; `npi` → "NPI". */
function label(key: string): string {
  const text = key.replace(/_/g, " ");
  if (/^npi\b/i.test(text)) return `NPI${text.slice(3)}`;
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Fetches the evidence PDF and saves it, so a failed request shows an error here instead of leaving the app. */
async function downloadEvidence(verificationId: number): Promise<void> {
  const res = await fetch(evidenceUrl(verificationId));
  if (!res.ok) throw new Error(`Evidence PDF request failed (${res.status})`);
  const href = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = href;
  link.download = `verification-${verificationId}.pdf`;
  document.body.append(link);
  link.click();
  link.remove();
  // Give the browser a moment to start the download before releasing the blob.
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

function DetailValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") return <span className="text-muted-foreground">—</span>;
  if (typeof value === "boolean") return <>{value ? "Yes" : "No"}</>;
  if (typeof value === "object") {
    return (
      <pre className="overflow-x-auto rounded-md bg-muted p-2 text-xs whitespace-pre-wrap break-all">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  }
  return <>{String(value)}</>;
}

/** Empty and notice text, styled like the section messages on the other screens. */
function SectionMessage({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn("py-8 text-center text-sm text-muted-foreground", className)}>{children}</p>;
}

function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {children}
    </p>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="font-heading text-base leading-snug font-medium">{title}</h3>
      {children}
    </section>
  );
}

function Row({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-3 py-2">
      <dt className="text-muted-foreground">{term}</dt>
      <dd className="min-w-0 break-words tabular-nums">{children}</dd>
    </div>
  );
}

/** Side panel with what was checked for one credential, when, against which source, and the evidence PDF. */
export function EvidenceDrawer({
  credential,
  open,
  onOpenChange,
}: {
  credential: Credential | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  // Refetch before the toast so the drawer and table have already updated when it appears.
  const verify = useMutation({
    mutationFn: (c: Credential) => api.verifyCredential(c.id),
    onSuccess: async (verification, c) => {
      await queryClient.invalidateQueries();
      const { tone, title, description } = verificationFeedback(c.credential_type, verification);
      toast[tone](title, { description });
    },
    onError: () => {
      toast.error("Verification did not run", { description: "Could not reach the API. Nothing was changed." });
    },
  });
  const download = useMutation({ mutationFn: downloadEvidence });

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        // Clear finished errors so they don't reappear the next time the drawer opens.
        if (!next) {
          if (!verify.isPending) verify.reset();
          if (!download.isPending) download.reset();
        }
        onOpenChange(next);
      }}
    >
      <SheetContent className="data-[side=right]:w-full data-[side=right]:sm:max-w-[420px]">
        {credential && (
          <DrawerBody
            credential={credential}
            running={verify.isPending && verify.variables.id === credential.id}
            verifyFailed={verify.isError && verify.variables.id === credential.id}
            onVerify={() => verify.mutate(credential)}
            downloading={download.isPending && download.variables === credential.last_verification?.id}
            downloadFailed={download.isError && download.variables === credential.last_verification?.id}
            onDownload={(verificationId) => download.mutate(verificationId)}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

function DrawerBody({
  credential: c,
  running,
  verifyFailed,
  onVerify,
  downloading,
  downloadFailed,
  onDownload,
}: {
  credential: Credential;
  running: boolean;
  verifyFailed: boolean;
  onVerify: () => void;
  downloading: boolean;
  downloadFailed: boolean;
  onDownload: (verificationId: number) => void;
}) {
  const v = c.last_verification;
  const details = v ? Object.entries(v.details).filter(([key]) => !isInternal(key, v.result)) : [];
  const manual = c.verify_method === "manual";

  return (
    <>
      <SheetHeader className="gap-1.5 border-b pr-12">
        <SheetTitle>Evidence</SheetTitle>
        <SheetDescription>
          {c.credential_type} · {c.associate_name}
        </SheetDescription>
        <p className="text-sm text-muted-foreground tabular-nums">
          {c.number ? `Number ${c.number}` : "No number on file"} ·{" "}
          {c.expires_date ? `Expires ${c.expires_date}` : c.status === "unverified" ? "Expiry not on file" : "Does not expire"}
        </p>
        <div>
          <StatusBadge status={c.status} />
        </div>
      </SheetHeader>

      {/* Only this middle part scrolls, so the header and the verify button stay in view at high zoom. */}
      <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-4 text-sm">
        {c.status === "excluded" && (
          <div role="alert" className="flex gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
            <Ban className="mt-0.5 size-4 shrink-0" aria-hidden />
            <p>
              <span className="font-medium">On the OIG exclusion list.</span> Do not schedule; notify HR.
            </p>
          </div>
        )}
        {verifyFailed && <ErrorBanner>Verification did not run. Could not reach the API. Nothing was changed.</ErrorBanner>}

        {v ? (
          <div
            aria-busy={running}
            aria-live="polite"
            className={cn("space-y-6 transition-opacity", running && "opacity-60")}
          >
            <Section title="Latest check">
              <dl className="divide-y">
                <Row term="Result">
                  <ResultBadge result={v.result} />
                </Row>
                <Row term="Source">
                  <span className="inline-flex items-center gap-1.5">
                    {v.source}
                    {c.verify_method === "mock" && <MockBadge />}
                  </span>
                </Row>
                <Row term="Checked">{checkedAt(v.checked_at)}</Row>
              </dl>
            </Section>

            <Section title="Details">
              {v.result === "error" ? (
                <SectionMessage className="py-4">
                  Could not reach {v.source}. Status is unchanged; try again later.
                </SectionMessage>
              ) : details.length > 0 ? (
                <dl className="divide-y">
                  {details.map(([key, value]) => (
                    <Row key={key} term={label(key)}>
                      <DetailValue value={value} />
                    </Row>
                  ))}
                </dl>
              ) : (
                <SectionMessage className="py-4">The source returned no extra details.</SectionMessage>
              )}
            </Section>

            <div className="space-y-3">
              <Button variant="outline" onClick={() => onDownload(v.id)} disabled={downloading}>
                {downloading ? <LoaderCircle className="animate-spin" aria-hidden /> : <Download aria-hidden />}
                {downloading ? "Preparing PDF…" : "Download evidence PDF"}
              </Button>
              {downloadFailed && <ErrorBanner>Couldn&apos;t download the evidence PDF. Try again.</ErrorBanner>}
            </div>
          </div>
        ) : (
          <div className="space-y-3 rounded-lg border py-8 text-center">
            <UnverifiedBadge />
            <p className="px-4 text-muted-foreground">
              {manual
                ? `Checked by hand at ${c.issuing_source}.${c.lookup_url ? " Use the lookup link below." : ""}`
                : `This credential has not been checked against ${c.issuing_source} yet.`}
            </p>
          </div>
        )}
      </div>

      {manual ? (
        // Checked by a person at the source; the app never looks these up itself.
        c.lookup_url && (
          <SheetFooter className="items-end border-t">
            <a href={lookupLink(c) ?? c.lookup_url} target="_blank" rel="noreferrer" className={buttonVariants()}>
              <ExternalLink aria-hidden />
              Look up at {c.issuing_source}
            </a>
          </SheetFooter>
        )
      ) : (
        <SheetFooter className="items-end border-t">
          <Button onClick={onVerify} disabled={running} variant={v ? "outline" : "default"}>
            <RefreshCw className={running ? "animate-spin" : undefined} aria-hidden />
            {running ? "Verifying…" : v ? "Verify this again" : "Verify now"}
          </Button>
        </SheetFooter>
      )}
    </>
  );
}
