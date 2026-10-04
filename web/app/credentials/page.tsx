"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { CredentialTable } from "@/components/CredentialTable";
import { CredentialEmailButton } from "@/components/CredentialEmailButton";
import { useRole } from "@/components/Providers";
import { useScope } from "@/components/ScopeFilters";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const LIMIT = 200;

/** Loading, empty and error text inside a card, styled like the Dashboard's section messages. */
function SectionMessage({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("space-y-1 py-8 text-center text-sm text-muted-foreground", className)}>{children}</div>;
}

function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {children}
    </p>
  );
}

/** Placeholder rows at about the height of the loaded table, so the card doesn't jump when data arrives. */
function TableSkeleton() {
  return (
    <div className="space-y-2" role="status" aria-label="Loading credentials">
      <Skeleton className="h-6 w-full" />
      {Array.from({ length: 8 }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export default function CredentialsPage() {
  const { role } = useRole();
  const { scope, filters } = useScope();
  const credentials = useQuery({
    queryKey: ["credentials", scope, "all"],
    queryFn: () => api.credentialsPage({ ...scope, limit: LIMIT }),
    placeholderData: keepPreviousData,
  });
  const data = credentials.data;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Credentials</h1>
        {filters}
      </div>
      {credentials.error &&
        (data ? (
          <ErrorBanner>
            Could not refresh credentials ({credentials.error.message}). Showing the last loaded list.
          </ErrorBanner>
        ) : (
          <ErrorBanner>
            Could not reach the API ({credentials.error.message}). Is the backend running on port 8000?
          </ErrorBanner>
        ))}
      <Card>
        <CardHeader>
          <CardTitle>All credentials</CardTitle>
          <CardDescription>
            {credentials.isLoading && <Skeleton className="h-5 w-64 max-w-full" />}
            {data &&
              `Most urgent first · ${data.total.toLocaleString()} credentials` +
                (data.total > LIMIT ? `, showing the ${LIMIT} most urgent` : "")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data ? (
            data.items.length === 0 ? (
              role === "manager" ? (
                <SectionMessage>
                  <p>No credentials on file for your team yet.</p>
                </SectionMessage>
              ) : (
                <SectionMessage>
                  <p className="font-medium text-foreground">No credentials match these filters.</p>
                  <p>Try a different facility, department, or manager.</p>
                </SectionMessage>
              )
            ) : (
              // With the Associate column the table is wider than the page even at 100%, so let the associate's
              // department line and the Credential, Expires and Last verified cells (2nd, 4th, 6th) wrap when space
              // runs out; the Evidence action then fits without scrolling. Scoped to this page.
              <div
                className={cn(
                  "[&_td:nth-child(1)_div]:whitespace-normal [&_td:nth-child(2)]:whitespace-normal [&_td:nth-child(4)]:whitespace-normal [&_td:nth-child(6)]:whitespace-normal",
                  credentials.isPlaceholderData && "opacity-60",
                )}
                aria-busy={credentials.isFetching}
              >
                <CredentialTable
                  credentials={data.items}
                  action={(credential) => <CredentialEmailButton credential={credential} />}
                />
              </div>
            )
          ) : credentials.error ? (
            <SectionMessage>
              <p>Couldn&apos;t load credentials.</p>
            </SectionMessage>
          ) : (
            <TableSkeleton />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
