"use client";

import { useQuery } from "@tanstack/react-query";

import { CredentialTable } from "@/components/CredentialTable";
import { useScope } from "@/components/ScopeFilters";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";

const LIMIT = 200;

export default function CredentialsPage() {
  const { scope, filters } = useScope();
  const credentials = useQuery({
    queryKey: ["credentials", scope, "all"],
    queryFn: () => api.credentials({ ...scope, limit: LIMIT }),
  });

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Credentials</h1>
        {filters}
      </div>
      {credentials.error && (
        <p role="alert" className="text-sm text-red-800">Could not load credentials ({credentials.error.message}).</p>
      )}
      <Card>
        <CardContent>
          {credentials.data ? (
            <>
              <CredentialTable credentials={credentials.data} />
              {credentials.data.length === LIMIT && (
                <p className="pt-3 text-xs text-muted-foreground">Showing the {LIMIT} most urgent. Narrow the filters to see more.</p>
              )}
            </>
          ) : (
            !credentials.error && <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
