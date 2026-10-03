"use client";

import { Button } from "@/components/ui/button";
import { type Role, useRole } from "@/components/Providers";

const ROLES: { value: Role; label: string }[] = [
  { value: "manager", label: "Manager" },
  { value: "hr", label: "HR" },
];

export function RoleSwitcher() {
  const { role, setRole } = useRole();
  return (
    <div role="group" aria-label="View as" className="flex items-center gap-1 rounded-lg border p-0.5">
      {ROLES.map((r) => (
        <Button
          key={r.value}
          size="sm"
          variant={role === r.value ? "default" : "ghost"}
          aria-pressed={role === r.value}
          onClick={() => setRole(r.value)}
        >
          {r.label}
        </Button>
      ))}
    </div>
  );
}
