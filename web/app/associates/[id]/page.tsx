"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { CredentialTable } from "@/components/CredentialTable";
import { CredentialTimeline } from "@/components/CredentialTimeline";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { type Feedback, summaryFeedback, verificationFeedback } from "@/components/VerifyFeedback";
import { api, type Credential } from "@/lib/api";

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

function LoadingState() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading associate">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <Skeleton className="h-40 w-full rounded-xl" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

export default function AssociatePage() {
  const id = Number(useParams<{ id: string }>().id);
  const queryClient = useQueryClient();
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

  if (associate.error) {
    return (
      <div className="space-y-4">
        <BackLink />
        <p role="alert" className="text-sm text-red-800">Could not load this associate ({associate.error.message}).</p>
      </div>
    );
  }
  if (!associate.data) return <LoadingState />;
  const a = associate.data;
  const verifiedCount = a.credentials.filter((c) => c.last_verification?.result === "verified").length;

  const verifyButton = (credential: Credential) => {
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
        {running ? "Verifying…" : "Verify"}
      </Button>
    );
  };

  return (
    <div className="space-y-6">
      <BackLink />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold">{a.name}</h1>
            {a.worst_status && <StatusBadge status={a.worst_status} />}
          </div>
          <p className="text-sm text-muted-foreground">
            {a.role} · {a.department} · {a.facility} ({a.state}){a.npi && ` · NPI ${a.npi}`}
          </p>
          <p className="text-sm text-muted-foreground">
            Reports to {a.manager_email} · {verifiedCount} of {a.credentials.length} verified
          </p>
        </div>
        <Button onClick={() => verifyAll.mutate()} disabled={busy || a.credentials.length === 0}>
          <RefreshCw className={verifyAll.isPending ? "animate-spin" : undefined} aria-hidden />
          {verifyAll.isPending ? "Verifying…" : "Verify now"}
        </Button>
      </div>
      {a.credentials.length === 0 ? (
        <Card>
          <CardContent>
            <p className="py-8 text-center text-sm text-muted-foreground">No credentials on file for this role yet.</p>
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
              <CredentialTable credentials={a.credentials} showAssociate={false} action={verifyButton} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
