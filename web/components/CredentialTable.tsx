"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EvidenceDrawer } from "@/components/EvidenceDrawer";
import { MockBadge, StatusBadge, UnverifiedBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Credential } from "@/lib/api";
import { checkedAt } from "@/lib/format";

function expiry(c: Credential): string {
  if (c.expires_date === null || c.days_left === null) return "Does not expire";
  if (c.days_left < 0) return `${c.expires_date} (${-c.days_left}d ago)`;
  return `${c.expires_date} (${c.days_left}d)`;
}

export function CredentialTable({
  credentials,
  showAssociate = true,
  action,
}: {
  credentials: Credential[];
  showAssociate?: boolean;
  action?: (credential: Credential) => React.ReactNode;
}) {
  // Prefer the row from the latest fetch so the drawer updates after "Verify again"; keep the
  // opened copy if a re-verify moves the credential out of a filtered list.
  const [selected, setSelected] = useState<Credential | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const evidenceFor = credentials.find((c) => c.id === selected?.id) ?? selected;

  const drawer = <EvidenceDrawer credential={evidenceFor} open={evidenceOpen} onOpenChange={setEvidenceOpen} />;

  if (credentials.length === 0) {
    return (
      <>
        <p className="py-8 text-center text-sm text-muted-foreground">No credentials match.</p>
        {drawer}
      </>
    );
  }
  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            {showAssociate && <TableHead>Associate</TableHead>}
            <TableHead>Credential</TableHead>
            <TableHead>Number</TableHead>
            <TableHead>Expires</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last verified</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {credentials.map((c) => (
            <TableRow key={c.id}>
              {showAssociate && (
                <TableCell>
                  <Link href={`/associates/${c.associate_id}`} className="font-medium hover:underline">
                    {c.associate_name}
                  </Link>
                  <div className="text-xs text-muted-foreground">
                    {c.department} · {c.facility}
                  </div>
                </TableCell>
              )}
              <TableCell>
                {c.credential_type}
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {c.issuing_source}
                  {c.verify_method === "mock" && <MockBadge />}
                </div>
              </TableCell>
              <TableCell className="tabular-nums">{c.number ?? "—"}</TableCell>
              <TableCell className="tabular-nums">{expiry(c)}</TableCell>
              <TableCell>
                <StatusBadge status={c.status} />
              </TableCell>
              <TableCell className="tabular-nums">
                {c.last_verification ? checkedAt(c.last_verification.checked_at) : <UnverifiedBadge />}
              </TableCell>
              <TableCell>
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={`Evidence for ${c.credential_type}`}
                    onClick={() => {
                      setSelected(c);
                      setEvidenceOpen(true);
                    }}
                  >
                    <FileText aria-hidden />
                    Evidence
                  </Button>
                  {action?.(c)}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {drawer}
    </>
  );
}
