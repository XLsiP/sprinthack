"use client";

import { FlaskConical } from "lucide-react";
import { useState, useSyncExternalStore } from "react";

import { ManagerSignIn } from "@/components/ManagerSignIn";
import { Button } from "@/components/ui/button";
import { useRole } from "@/components/Providers";
import { managerName } from "@/lib/format";

const HINT =
  "Demo only, not a real login. Manager shows one manager's team (you choose which); HR shows everyone.";

const noop = () => () => {};

export function RoleSwitcher() {
  const { role, setRole, manager } = useRole();
  const [asking, setAsking] = useState(false);
  // False while the server-rendered page is being picked up, when the stored role is not known yet.
  const ready = useSyncExternalStore(noop, () => true, () => false);
  // The Manager view needs to know whose team to show; ask if nobody has been chosen yet.
  const open = asking || (ready && role === "manager" && !manager);

  return (
    <div className="flex items-center gap-2" title={HINT}>
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        <FlaskConical className="size-3.5" aria-hidden />
        Demo view
      </span>
      <div role="group" aria-label="Demo view: choose role" className="flex items-center gap-1 rounded-lg border p-0.5">
        {/* Always asks, so it is also how to switch to another manager. */}
        <Button
          size="sm"
          variant={role === "manager" ? "default" : "ghost"}
          aria-pressed={role === "manager"}
          onClick={() => setAsking(true)}
        >
          <span className="max-w-40 truncate">
            {role === "manager" && manager ? `Manager: ${managerName(manager)}` : "Manager"}
          </span>
        </Button>
        <Button size="sm" variant={role === "hr" ? "default" : "ghost"} aria-pressed={role === "hr"} onClick={() => setRole("hr")}>
          HR
        </Button>
      </div>
      {/* Remounted each time it opens, so it starts on the current manager with an empty password. */}
      {open && <ManagerSignIn open onClose={() => setAsking(false)} />}
    </div>
  );
}
