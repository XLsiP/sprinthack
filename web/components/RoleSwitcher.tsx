"use client";

import { FlaskConical } from "lucide-react";

import { Button } from "@/components/ui/button";
import { type Role, useRole } from "@/components/Providers";

const ROLES: { value: Role; label: string }[] = [
  { value: "manager", label: "Manager" },
  { value: "hr", label: "HR" },
];

const HINT = "Demo only, not a real login. Switch between the Manager (your team) and HR (everyone) views.";

export function RoleSwitcher() {
  const { role, setRole } = useRole();
  return (
    <div className="flex items-center gap-2" title={HINT}>
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        <FlaskConical className="size-3.5" aria-hidden />
        Demo view
      </span>
      <div role="group" aria-label="Demo view: choose role" className="flex items-center gap-1 rounded-lg border p-0.5">
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
    </div>
  );
}
