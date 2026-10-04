"use client";

import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { DailyRunButton } from "@/components/DailyRunButton";
import { useRole } from "@/components/Providers";
import { RoleSwitcher } from "@/components/RoleSwitcher";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/credentials", label: "Credentials" },
  { href: "/verify", label: "Verify" },
  { href: "/alerts", label: "Alerts" },
];

export function Header() {
  const pathname = usePathname();
  const { role } = useRole();
  return (
    <header className="border-b bg-background print:hidden">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <ShieldCheck className="size-5 text-primary" aria-hidden />
          Credentialing Tracker
        </Link>
        <nav className="flex gap-1 text-sm">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-md px-2 py-1.5 text-muted-foreground sm:px-3 hover:text-foreground",
                pathname === item.href && "bg-muted font-medium text-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        {/* Wraps on phones so HR's "Run daily check" doesn't squeeze the role switcher. */}
        <div className="ml-auto flex flex-wrap items-center justify-end gap-3 gap-y-2">
          {role === "hr" && <DailyRunButton />}
          <RoleSwitcher />
        </div>
      </div>
    </header>
  );
}
