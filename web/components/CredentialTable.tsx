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

/** Date and days left as two unbreakable pieces, so a page that lets this cell wrap never splits the date. */
function expiry(c: Credential): React.ReactNode {
  if (c.status === "unverified") return "Not on file";
  if (c.expires_date === null || c.days_left === null) return "Does not expire";
  const left = c.days_left < 0 ? `(${-c.days_left}d ago)` : `(${c.days_left}d)`;
  return (
    <>
      <span className="whitespace-nowrap">{c.expires_date}</span> <span className="whitespace-nowrap">{left}</span>
    </>
  );
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
  // With the Associate column the rows change with the HR filters, so the columns whose content varies get set
  // widths (and the Associate cell wraps) to keep the table from jumping between filters.
  const width = (w: string) => (showAssociate ? w : undefined);
  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            {showAssociate && <TableHead className="w-[22%]">Associate</TableHead>}
            <TableHead className={width("w-[18%]")}>Credential</TableHead>
            <TableHead>Number</TableHead>
            <TableHead className={width("w-[13%]")}>Expires</TableHead>
            <TableHead className={width("w-38 min-w-38")}>Status</TableHead>
            <TableHead>Last verified</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {credentials.map((c) => (
            <TableRow key={c.id}>
              {showAssociate && (
                <TableCell className="whitespace-normal">
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
                    {/* Icon only on narrow screens (and at high zoom) so the actions column fits without scrolling. */}
                    <span className="max-lg:sr-only">Evidence</span>
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
