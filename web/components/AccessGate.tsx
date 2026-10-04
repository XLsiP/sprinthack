"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Brand } from "@/components/Brand";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { setAccessPassword } from "@/lib/access";
import { api } from "@/lib/api";

const STILL_WAKING_MS = 8000;

/** Centered card on a soft background with faint light beams; shared by the password and connecting screens. */
function GateLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="relative isolate flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-16">
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--color-teal-50),transparent_65%)]"
      />
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-[repeating-conic-gradient(from_150deg_at_50%_-10%,var(--color-sky-100)_0deg_3deg,transparent_3deg_10deg)] opacity-50 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]"
      />
      <Card className="w-full max-w-sm shadow-sm">
        <CardHeader className="text-center">
          <Brand size="lg" className="mx-auto mb-2 w-fit" />
          <CardDescription>Credential tracking for imaging teams</CardDescription>
        </CardHeader>
        {children}
      </Card>
    </main>
  );
}

/** Shown while the first API call is pending; on the free hosting tier the server can take up to a minute to wake. */
function ConnectingCard() {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), STILL_WAKING_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <GateLayout>
      <CardContent className="space-y-3">
        <div role="status" aria-live="polite" className="space-y-1 text-center text-sm text-muted-foreground">
          <p>Connecting to the server… the free hosting tier can take up to a minute to wake up.</p>
          {slow && <p>Still waking up…</p>}
        </div>
        <div className="space-y-2" aria-hidden>
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </CardContent>
    </GateLayout>
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
  const [visible, setVisible] = useState(false);

  if (access.isPending) return <ConnectingCard />;
  if (access.isError || !access.data.required || access.data.granted) return <>{children}</>;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setAccessPassword(value);
    setTried(true);
    await queryClient.invalidateQueries();
  };

  return (
    <GateLayout>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="space-y-3">
          <label htmlFor="access-password" className="text-sm font-medium">
            Access password
          </label>
          <div className="relative">
            <input
              id="access-password"
              type={visible ? "text" : "password"}
              autoComplete="current-password"
              autoFocus
              required
              value={value}
              onChange={(event) => setValue(event.target.value)}
              aria-invalid={tried && !access.isFetching}
              aria-describedby={tried ? "access-error" : undefined}
              className="h-9 w-full rounded-lg border border-input bg-background pr-10 pl-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-red-600"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Show password"
              aria-pressed={visible}
              onClick={() => setVisible((v) => !v)}
              className="absolute top-1/2 right-1 -translate-y-1/2 text-muted-foreground"
            >
              {visible ? <EyeOff aria-hidden /> : <Eye aria-hidden />}
            </Button>
          </div>
          {tried && !access.isFetching && (
            <p id="access-error" role="alert" className="text-sm text-red-800">
              Wrong password. Check it and try again.
            </p>
          )}
          <Button type="submit" className="w-full" disabled={access.isFetching}>
            {access.isFetching ? "Checking…" : "Continue"}
          </Button>
        </form>
        <p className="text-center text-xs text-muted-foreground">
          This demo uses a real staff roster, so access is password protected.
        </p>
      </CardContent>
    </GateLayout>
  );
}
