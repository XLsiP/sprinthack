"use client";

import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { createContext, useContext, useState, useSyncExternalStore } from "react";

import { api, type Scope } from "@/lib/api";
import { managerName } from "@/lib/format";

export type Role = "manager" | "hr";

// Demo stand-in for auth: the Manager view is one manager's team, HR sees everyone.
// The person picks which manager they are in the header (see ManagerSignIn). Until they have,
// the API names one (the largest team); the constants are only used until it answers.
const FALLBACK_MANAGER = "radiology.manager@example.org";
const FALLBACK_TEAM = "Radiology, Memorial Hospital of South Bend";

/** The manager whose team the Manager view shows, and a label for that team. */
export function useDemoManager(): { manager: string; team: string } {
  const { manager } = useContext(RoleContext);
  const filters = useQuery({ queryKey: ["filters"], queryFn: api.filters, staleTime: Infinity });
  if (manager) return { manager, team: `${managerName(manager)}'s team` };
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

// Which manager the Manager view is for (their email), chosen in the header and kept like the role.
const MANAGER_KEY = "beacon.manager";
let memoryManager: string | null = null;

function readManager(): string | null {
  try {
    return localStorage.getItem(MANAGER_KEY) ?? memoryManager;
  } catch {
    return memoryManager;
  }
}

function writeManager(manager: string) {
  memoryManager = manager;
  try {
    localStorage.setItem(MANAGER_KEY, manager);
  } catch {
    // Storage blocked; memoryManager carries it.
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

const RoleContext = createContext<{
  role: Role;
  setRole: (role: Role) => void;
  manager: string | null; // null until someone has chosen one in this browser
  setManager: (manager: string) => void;
}>({
  role: "manager",
  setRole: () => {},
  manager: null,
  setManager: () => {},
});

export function useRole() {
  return useContext(RoleContext);
}

// HR's facility / department / manager filters, shared by every page so they carry across navigation.
type HrScopeState = [Scope, React.Dispatch<React.SetStateAction<Scope>>];
const HrScopeContext = createContext<HrScopeState>([{}, () => {}]);

export function useHrScope() {
  return useContext(HrScopeContext);
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } }));
  const role = useSyncExternalStore(subscribe, readRole, () => "manager" as const);
  const manager = useSyncExternalStore(subscribe, readManager, () => null);
  const hrScope = useState<Scope>({});
  return (
    <QueryClientProvider client={queryClient}>
      <RoleContext.Provider value={{ role, setRole: writeRole, manager, setManager: writeManager }}>
        <HrScopeContext.Provider value={hrScope}>{children}</HrScopeContext.Provider>
      </RoleContext.Provider>
    </QueryClientProvider>
  );
}
