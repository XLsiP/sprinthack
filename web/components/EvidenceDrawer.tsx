"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Ban, Download, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { MockBadge, ResultBadge, StatusBadge, UnverifiedBadge } from "@/components/StatusBadge";
import { buttonVariants, Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { verificationFeedback } from "@/components/VerifyFeedback";
import { api, type Credential, evidenceUrl, type VerificationResult } from "@/lib/api";
import { checkedAt } from "@/lib/format";

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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</h3>
      {children}
    </section>
  );
}

function Row({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-3 py-1.5">
      <dt className="text-muted-foreground">{term}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
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

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-[420px]">
        {credential && (
          <DrawerBody
            credential={credential}
            running={verify.isPending && verify.variables.id === credential.id}
            onVerify={() => verify.mutate(credential)}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}

function DrawerBody({
  credential: c,
  running,
  onVerify,
}: {
  credential: Credential;
  running: boolean;
  onVerify: () => void;
}) {
  const v = c.last_verification;
  const details = v ? Object.entries(v.details).filter(([key]) => !isInternal(key, v.result)) : [];

  return (
    <>
      <SheetHeader className="pr-12">
        <SheetTitle>Evidence</SheetTitle>
        <SheetDescription>
          {c.credential_type} · {c.associate_name}
        </SheetDescription>
        <p className="pt-1 text-sm text-muted-foreground">
          {c.number ? `Number ${c.number}` : "No number on file"} ·{" "}
          {c.expires_date ? `Expires ${c.expires_date}` : "Does not expire"}
        </p>
        <div className="pt-1">
          <StatusBadge status={c.status} />
        </div>
      </SheetHeader>

      <div className="space-y-6 px-4 text-sm">
        {c.status === "excluded" && (
          <div role="alert" className="flex gap-2 rounded-lg bg-red-100 p-3 text-red-800">
            <Ban className="mt-0.5 size-4 shrink-0" aria-hidden />
            <p>
              <span className="font-medium">On the OIG exclusion list.</span> Do not schedule; notify HR.
            </p>
          </div>
        )}

        {v ? (
          <>
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
                <Row term="Checked">
                  <span className="tabular-nums">{checkedAt(v.checked_at)}</span>
                </Row>
              </dl>
            </Section>

            <Section title="Details">
              {v.result === "error" && (
                <p className="rounded-lg bg-gray-100 p-3 text-gray-700">Source unavailable — try again later.</p>
              )}
              {details.length > 0 ? (
                <dl className="divide-y">
                  {details.map(([key, value]) => (
                    <Row key={key} term={label(key)}>
                      <DetailValue value={value} />
                    </Row>
                  ))}
                </dl>
              ) : (
                v.result !== "error" && <p className="text-muted-foreground">The source returned no extra details.</p>
              )}
            </Section>

            <a href={evidenceUrl(v.id)} download className={buttonVariants({ variant: "outline" })}>
              <Download aria-hidden />
              Download evidence PDF
            </a>
          </>
        ) : (
          <div className="space-y-3 rounded-lg border border-dashed p-6 text-center">
            <UnverifiedBadge />
            <p className="text-muted-foreground">This credential has not been checked against {c.issuing_source} yet.</p>
          </div>
        )}
      </div>

      <SheetFooter className="items-end">
        <Button onClick={onVerify} disabled={running} variant={v ? "outline" : "default"}>
          <RefreshCw className={running ? "animate-spin" : undefined} aria-hidden />
          {running ? "Verifying…" : v ? "Verify this again" : "Verify now"}
        </Button>
      </SheetFooter>
    </>
  );
}
