"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LockKeyhole } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { setAccessPassword } from "@/lib/access";
import { api } from "@/lib/api";

/**
 * Asks for the shared access password when the API requires one, and shows the app once it is accepted.
 * If the API has no password, or cannot be reached, the app renders as usual and reports its own errors.
 */
export function AccessGate({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const access = useQuery({ queryKey: ["access"], queryFn: api.access, staleTime: Infinity, retry: false });
  const [value, setValue] = useState("");
  const [tried, setTried] = useState(false);

  if (access.isPending) return null;
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
