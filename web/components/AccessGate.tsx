"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LockKeyhole, Server } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { setAccessPassword } from "@/lib/access";
import { api } from "@/lib/api";

const STILL_WAKING_MS = 8000;

/** Shown while the first API call is pending; on the free hosting tier the server can take up to a minute to wake. */
function ConnectingCard() {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), STILL_WAKING_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-6 py-16">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="size-4" aria-hidden />
            Credentialing Tracker
          </CardTitle>
          <div role="status" aria-live="polite" className="space-y-1">
            <CardDescription>
              Connecting to the server… the free hosting tier can take up to a minute to wake up.
            </CardDescription>
            {slow && <CardDescription>Still waking up…</CardDescription>}
          </div>
        </CardHeader>
        <CardContent className="space-y-2" aria-hidden>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardContent>
      </Card>
    </main>
  );
}

/**
 * Asks for the shared access password when the API requires one, and shows the app once it is accepted.
 * If the API has no password, or cannot be reached, the app renders as usual and reports its own errors.
 */
export function AccessGate({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const access = useQuery({ queryKey: ["access"], queryFn: api.access, staleTime: Infinity, retry: false });
  const [value, setValue] = useState("");
  const [tried, setTried] = useState(false);

  if (access.isPending) return <ConnectingCard />;
  if (access.isError || !access.data.required || access.data.granted) return <>{children}</>;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setAccessPassword(value);
    setTried(true);
    await queryClient.invalidateQueries();
  };

  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-6 py-16">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LockKeyhole className="size-4" aria-hidden />
            Credentialing Tracker
          </CardTitle>
          <CardDescription>This site shows staff information. Enter the access password to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-3">
            <label htmlFor="access-password" className="text-sm font-medium">
              Access password
            </label>
            <input
              id="access-password"
              type="password"
              autoComplete="current-password"
              autoFocus
              required
              value={value}
              onChange={(event) => setValue(event.target.value)}
              aria-invalid={tried && !access.isFetching}
              aria-describedby={tried ? "access-error" : undefined}
              className="h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            />
            {tried && !access.isFetching && (
              <p id="access-error" role="alert" className="text-sm text-red-800">
                That password was not accepted.
              </p>
            )}
            <Button type="submit" className="w-full" disabled={access.isFetching}>
              {access.isFetching ? "Checking…" : "Continue"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
