"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useState, useSyncExternalStore } from "react";

export type Role = "manager" | "hr";

// Demo stand-in for auth: the Manager view is this manager's team, HR sees everyone.
export const DEMO_MANAGER = "radiology.manager@example.org";

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
