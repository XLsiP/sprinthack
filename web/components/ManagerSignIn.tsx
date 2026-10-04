"use client";

import { Dialog } from "@base-ui/react/dialog";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useRole } from "@/components/Providers";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { managerName } from "@/lib/format";
import { cn } from "@/lib/utils";

const FIELD =
  "h-9 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

/**
 * Asks which manager is using the Manager view, and for the access password again, before showing
 * that manager's team. Demo stand-in for a login: the password is the app's one shared password,
 * so it guards against switching by accident rather than proving who someone is.
 */
export function ManagerSignIn({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { manager, setManager, setRole } = useRole();
  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters, staleTime: Infinity });
  const access = useQuery({ queryKey: ["access"], queryFn: api.access, staleTime: Infinity, retry: false });
  const [picked, setPicked] = useState(manager ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const managers = filters.data?.managers ?? [];
  const needsPassword = access.data?.required ?? false;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setChecking(true);
    try {
      if (needsPassword && !(await api.checkAccess(password))) {
        setError("Wrong password. Check it and try again.");
        return;
      }
      setManager(picked);
      setRole("manager");
      setPassword("");
      onClose();
    } catch {
      setError("Could not reach the server. Try again.");
    } finally {
      setChecking(false);
    }
  };

  return (
    // Until a manager has been chosen there is no team to show, so the only ways out are choosing one or the HR view.
    <Dialog.Root open={open} onOpenChange={(next) => !next && manager && onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/20 supports-backdrop-filter:backdrop-blur-xs" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 z-50 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-popover p-6 text-sm text-popover-foreground shadow-lg">
          <Dialog.Title className="text-base font-semibold">Manager view</Dialog.Title>
          <Dialog.Description className="mt-1 text-muted-foreground">
            Choose who you are to see only your team.
          </Dialog.Description>
          <form onSubmit={submit} className="mt-4 space-y-4">
            <fieldset className="space-y-2">
              <legend className="font-medium">Which manager are you?</legend>
              {filters.isPending && <p className="text-muted-foreground">Loading…</p>}
              <div className="max-h-56 space-y-1 overflow-y-auto">
                {managers.map((email) => (
                  <label
                    key={email}
                    title={email}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2",
                      picked === email && "border-ring bg-muted",
                    )}
                  >
                    <input
                      type="radio"
                      name="manager"
                      value={email}
                      checked={picked === email}
                      onChange={() => setPicked(email)}
                      required
                    />
                    {managerName(email)}
                  </label>
                ))}
              </div>
            </fieldset>
            {needsPassword && (
              <label className="block space-y-1">
                <span className="font-medium">Access password</span>
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  aria-invalid={Boolean(error)}
                  className={cn(FIELD, "aria-invalid:border-red-600")}
                />
              </label>
            )}
            {error && (
              <p role="alert" className="text-red-800">
                {error}
              </p>
            )}
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  if (!manager) setRole("hr");
                  onClose();
                }}
              >
                {manager ? "Cancel" : "Use the HR view"}
              </Button>
              <Button type="submit" disabled={checking || !picked}>
                {checking ? "Checking…" : "Show my team"}
              </Button>
            </div>
          </form>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
