"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useState } from "react";

export type Role = "manager" | "hr";

// Demo stand-in for auth: the Manager view is this manager's team, HR sees everyone.
export const DEMO_MANAGER = "radiology.manager@example.org";

const RoleContext = createContext<{ role: Role; setRole: (role: Role) => void }>({
  role: "manager",
  setRole: () => {},
});

export function useRole() {
  return useContext(RoleContext);
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } }));
  const [role, setRole] = useState<Role>("manager");
  return (
    <QueryClientProvider client={queryClient}>
      <RoleContext.Provider value={{ role, setRole }}>{children}</RoleContext.Provider>
    </QueryClientProvider>
  );
}
