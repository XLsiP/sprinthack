"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useParams } from "next/navigation";

import { CredentialTable } from "@/components/CredentialTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function AssociatePage() {
  const id = Number(useParams<{ id: string }>().id);
  const queryClient = useQueryClient();
  const associate = useQuery({ queryKey: ["associate", id], queryFn: () => api.associate(id) });
  const verify = useMutation({
    mutationFn: () => api.verifyAssociate(id),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  if (associate.error) {
    return <p role="alert" className="text-sm text-red-800">Could not load this associate ({associate.error.message}).</p>;
  }
  if (!associate.data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const a = associate.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{a.name}</h1>
          <p className="text-sm text-muted-foreground">
            {a.role} · {a.department} · {a.facility} ({a.state}){a.npi && ` · NPI ${a.npi}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {verify.error && <p role="alert" className="text-sm text-red-800">Verification failed to run.</p>}
          {verify.data && (
            <p className="text-sm text-muted-foreground" role="status">
              {verify.data.filter((v) => v.result === "verified").length} of {verify.data.length} verified
            </p>
          )}
          <Button onClick={() => verify.mutate()} disabled={verify.isPending}>
            <RefreshCw className={verify.isPending ? "animate-spin" : undefined} aria-hidden />
            {verify.isPending ? "Verifying…" : "Verify now"}
          </Button>
        </div>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Credentials</CardTitle>
          <CardDescription>Reports to {a.manager_email}</CardDescription>
        </CardHeader>
        <CardContent>
          <CredentialTable credentials={a.credentials} showAssociate={false} />
        </CardContent>
      </Card>
    </div>
  );
}
