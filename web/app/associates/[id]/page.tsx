"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, Printer, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { CredentialTable } from "@/components/CredentialTable";
import { CredentialTimeline } from "@/components/CredentialTimeline";
import { useDemoManager, useRole } from "@/components/Providers";
import { resultLabel, STATUS, StatusBadge } from "@/components/StatusBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
 alex/lookup-helper
import { type Feedback, summaryFeedback, verificationFeedback } from "@/components/VerifyFeedback";
import { api, type Credential } from "@/lib/api";
import { lookupLink } from "@/lib/lookup";
import { managerName } from "@/lib/format";

import { type Feedback, needsReview, summaryFeedback, verificationFeedback } from "@/components/VerifyFeedback";
import { api, type AssociateDetail, type Credential } from "@/lib/api";
import { checkedAt, localDate, managerName } from "@/lib/format";
 main
import { cn } from "@/lib/utils";

function notify({ tone, title, description }: Feedback) {
  toast[tone](title, { description });
}

function notifyFailure() {
  toast.error("Verification did not run", { description: "Could not reach the API. Nothing was changed." });
}

function BackLink() {
  return (
    <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft className="size-4" aria-hidden />
      Back to dashboard
    </Link>
  );
}

/** Empty and notice text inside a card, styled like the Dashboard's section messages. */
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

function expires(c: Credential): string {
  if (c.expires_date) return c.expires_date;
  return c.status === "unverified" ? "Not on file" : "Does not expire";
}

/** One-page credential file for the associate's paper file; only shown when printing. */
function PrintableFile({ associate: a }: { associate: AssociateDetail }) {
  const cell = "border border-black px-1.5 py-1 align-top";
  return (
    <div className="hidden space-y-4 text-black print:block">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold">Credential file</h1>
        <p className="text-base font-medium">{a.name}</p>
        <dl className="grid grid-cols-[6rem_1fr] gap-x-3 text-sm">
          <dt>Role</dt>
          <dd>{a.role}</dd>
          <dt>Department</dt>
          <dd>{a.department}</dd>
          <dt>Facility</dt>
          <dd>
            {a.facility} ({a.state})
          </dd>
          <dt>Manager</dt>
          <dd>{managerName(a.manager_email)}</dd>
        </dl>
      </div>
      <table className="w-full border-collapse text-left text-xs tabular-nums">
        <thead>
          <tr>
            {["Credential", "Issuing source", "Number", "Expires", "Status", "Last checked", "Last result", "Evidence"].map(
              (h) => (
                <th key={h} className={cn(cell, "font-semibold")}>
                  {h}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {a.credentials.map((c) => {
            const v = c.last_verification;
            return (
              <tr key={c.id} className="break-inside-avoid">
                <td className={cell}>{c.credential_type}</td>
                <td className={cell}>{c.issuing_source}</td>
                <td className={cell}>{c.number ?? "Not on file"}</td>
                <td className={cell}>{expires(c)}</td>
                <td className={cell}>{STATUS[c.status].label}</td>
                <td className={cell}>{v ? checkedAt(v.checked_at).slice(0, 10) : "Never"}</td>
                <td className={cell}>{v ? resultLabel(v.result, needsReview(v)) : "—"}</td>
                <td className={cell}>{v ? `#${v.id}` : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="text-xs">
        Generated {localDate(new Date())} from primary-source checks by Beacon Credentialing Tracker. Retain in the
        associate&apos;s credential file.
      </p>
    </div>
  );
}

/** Placeholder with the same header, cards and titles as the loaded page, so nothing jumps when data arrives. */
function LoadingState() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading associate">
      <div className="space-y-2">
        <BackLink />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-96 max-w-full" />
            <Skeleton className="h-4 w-72 max-w-full" />
          </div>
          <Skeleton className="h-8 w-28" />
        </div>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Credential timeline</CardTitle>
          <CardDescription>Issue date to expiry for each credential</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="grid grid-cols-1 gap-2 sm:grid-cols-[13rem_1fr] sm:gap-x-4">
              <Skeleton className="h-9" />
              <Skeleton className="h-4 self-center" />
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Credentials</CardTitle>
          <CardDescription>Most urgent first</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-6 w-full" />
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default function AssociatePage() {
  const id = Number(useParams<{ id: string }>().id);
  const queryClient = useQueryClient();
  const { role } = useRole();
  const { manager: demoManager } = useDemoManager();
  const associate = useQuery({ queryKey: ["associate", id], queryFn: () => api.associate(id) });

  // Refetch before the toast so the badge and "Last verified" have already updated when it appears.
  const verifyOne = useMutation({
    mutationFn: (credential: Credential) => api.verifyCredential(credential.id),
    onSuccess: async (verification, credential) => {
      await queryClient.invalidateQueries();
      notify(verificationFeedback(credential.credential_type, verification));
    },
    onError: notifyFailure,
  });
  const verifyAll = useMutation({
    mutationFn: () => api.verifyAssociate(id),
    onSuccess: async (verifications) => {
      await queryClient.invalidateQueries();
      const names = new Map(associate.data?.credentials.map((c) => [c.id, c.credential_type]));
      notify(summaryFeedback(verifications, names));
    },
    onError: notifyFailure,
  });
  const busy = verifyOne.isPending || verifyAll.isPending;

  if (!associate.data) {
    if (!associate.error) return <LoadingState />;
    return (
      <div className="space-y-4">
        <BackLink />
        <ErrorBanner>Could not load this associate ({associate.error.message}).</ErrorBanner>
      </div>
    );
  }
  const a = associate.data;
  const automatic = a.credentials.filter((c) => c.verify_method !== "manual").length;
  if (role === "manager" && a.manager_email !== demoManager) {
    return (
      <div className="space-y-4">
        <BackLink />
        <Card>
          <CardContent>
            <div className="space-y-1 py-8 text-center">
              <p className="font-medium">This associate isn&apos;t on your team.</p>
              <p className="text-sm text-muted-foreground">Switch to the HR view in the header to see everyone.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }
  const verifiedCount = a.credentials.filter((c) => c.last_verification?.result === "verified").length;

  const verifyButton = (credential: Credential) => {
    if (credential.verify_method === "manual") {
      // Checked by a person at the source; the app never looks these up itself.
      return credential.lookup_url ? (
        <a
          href={lookupLink(credential) ?? credential.lookup_url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Look up ${credential.credential_type} at ${credential.issuing_source}`}
          className={buttonVariants({ size: "sm", variant: "outline" })}
        >
          <ExternalLink aria-hidden />
          <span className="max-lg:sr-only">Look up</span>
        </a>
      ) : null;
    }
    const running = verifyAll.isPending || (verifyOne.isPending && verifyOne.variables.id === credential.id);
    return (
      <Button
        size="sm"
        variant="outline"
        aria-label={`Verify ${credential.credential_type}`}
        disabled={busy}
        onClick={() => verifyOne.mutate(credential)}
      >
        <RefreshCw className={running ? "animate-spin" : undefined} aria-hidden />
        {/* Icon only on narrow screens (and at high zoom) so the actions column fits without scrolling. */}
        <span className="max-lg:sr-only">{running ? "Verifying…" : "Verify"}</span>
      </Button>
    );
  };

  return (
    <>
      <div className="space-y-6 print:hidden">
        <div className="space-y-2">
          <BackLink />
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-semibold tracking-tight">{a.name}</h1>
                {a.worst_status && <StatusBadge status={a.worst_status} />}
              </div>
              <p className="text-sm text-muted-foreground">
                {a.role} · {a.department} · {a.facility} ({a.state})
                {a.npi && (
                  <>
                    {" · NPI "}
                    <span className="tabular-nums">{a.npi}</span>
                  </>
                )}
              </p>
              <p className="text-sm text-muted-foreground">
                Reports to <span title={a.manager_email}>{managerName(a.manager_email)}</span>
              </p>
            </div>
            <div className="flex items-center gap-3">
              <p className="text-sm text-muted-foreground tabular-nums" role="status">
                {verifiedCount} of {a.credentials.length} checked
              </p>
              <Button
                onClick={() => verifyAll.mutate()}
                disabled={busy || automatic === 0}
                title={automatic === 0 && a.credentials.length > 0 ? "These credentials are checked by hand at the source" : undefined}
              >
                <RefreshCw className={verifyAll.isPending ? "animate-spin" : undefined} aria-hidden />
                {verifyAll.isPending ? "Verifying…" : "Verify now"}
              </Button>
              <Button variant="outline" onClick={() => window.print()}>
                <Printer aria-hidden />
                Print credential file
              </Button>
            </div>
          </div>
        </div>
        {associate.error && (
          <ErrorBanner>Could not refresh this associate ({associate.error.message}). Showing the last loaded details.</ErrorBanner>
        )}
        {a.credentials.length === 0 ? (
          <Card>
            <CardContent>
              <SectionMessage>No credentials on file for this role yet.</SectionMessage>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Credential timeline</CardTitle>
                <CardDescription>Issue date to expiry for each credential</CardDescription>
              </CardHeader>
              <CardContent>
                <CredentialTimeline credentials={a.credentials} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Credentials</CardTitle>
                <CardDescription>Most urgent first</CardDescription>
              </CardHeader>
              <CardContent>
                {/* Below lg (narrow windows, 150% zoom) let the Credential and Last verified columns (1st and 5th
                    with showAssociate={false}) wrap so the actions fit without scrolling. Scoped to this page. */}
                <div className="max-lg:[&_td:nth-child(1)]:whitespace-normal max-lg:[&_td:nth-child(5)]:whitespace-normal">
                  <CredentialTable credentials={a.credentials} showAssociate={false} action={verifyButton} />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
      <PrintableFile associate={a} />
    </>
  );
}
