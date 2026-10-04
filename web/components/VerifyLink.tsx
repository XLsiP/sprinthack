import { ClipboardCheck } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import type { Credential } from "@/lib/api";

/** For a credential a person checks by hand: opens the Verify page on that credential. Nothing for the others. */
export function VerifyLink({ credential }: { credential: Credential }) {
  if (credential.verify_method !== "manual") return null;
  return (
    <Link
      href={`/verify?credential=${credential.id}`}
      aria-label={`Verify ${credential.credential_type} for ${credential.associate_name}`}
      className={buttonVariants({ size: "sm", variant: "outline" })}
    >
      <ClipboardCheck aria-hidden />
      <span className="max-lg:sr-only">Verify</span>
    </Link>
  );
}
