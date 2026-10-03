"use client";

import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { createContext, useContext, useState, useSyncExternalStore } from "react";

import { api } from "@/lib/api";

export type Role = "manager" | "hr";

// Demo stand-in for auth: the Manager view is one manager's team, HR sees everyone.
// The API names the manager (the largest team); these are only used until it answers.
const FALLBACK_MANAGER = "radiology.manager@example.org";
const FALLBACK_TEAM = "Radiology, Memorial Hospital of South Bend";

/** The manager whose team the Manager view shows, and a label for that team. */
export function useDemoManager(): { manager: string; team: string } {
  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters, staleTime: Infinity });
  return {
    manager: filters.data?.demo_manager ?? FALLBACK_MANAGER,
    team: filters.data?.demo_team ?? FALLBACK_TEAM,
  };
}

// The demo role is kept in localStorage so it survives reloads, new tabs and typed URLs.
const ROLE_KEY = "beacon.role";
const listeners = new Set<() => void>();
// Fallback when storage is blocked: the role still switches, it just won't survive a reload.
let memoryRole: Role = "manager";

function readRole(): Role {
  try {
    const stored = localStorage.getItem(ROLE_KEY);
    return stored === "hr" || stored === "manager" ? stored : memoryRole;
  } catch {
    return memoryRole;
  }
}

function writeRole(role: Role) {
  memoryRole = role;
  try {
    localStorage.setItem(ROLE_KEY, role);
  } catch {
    // Storage blocked; memoryRole carries it.
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

const RoleContext = createContext<{ role: Role; setRole: (role: Role) => void }>({
  role: "manager",
  setRole: () => {},
});

export function useRole() {
  return useContext(RoleContext);
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } }));
  const role = useSyncExternalStore(subscribe, readRole, () => "manager" as const);
  return (
    <QueryClientProvider client={queryClient}>
      <RoleContext.Provider value={{ role, setRole: writeRole }}>{children}</RoleContext.Provider>
    </QueryClientProvider>
  );
}
