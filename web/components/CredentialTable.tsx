import Link from "next/link";

import { StatusBadge, UnverifiedBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Credential } from "@/lib/api";

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
  if (credentials.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No credentials match.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {showAssociate && <TableHead>Associate</TableHead>}
          <TableHead>Credential</TableHead>
          <TableHead>Number</TableHead>
          <TableHead>Expires</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Last verified</TableHead>
          {action && <TableHead />}
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
              <div className="text-xs text-muted-foreground">{c.issuing_source}</div>
            </TableCell>
            <TableCell className="tabular-nums">{c.number ?? "—"}</TableCell>
            <TableCell className="tabular-nums">{expiry(c)}</TableCell>
            <TableCell>
              <StatusBadge status={c.status} />
            </TableCell>
            <TableCell className="tabular-nums">
              {c.last_verification ? c.last_verification.checked_at.slice(0, 10) : <UnverifiedBadge />}
            </TableCell>
            {action && <TableCell className="text-right">{action(c)}</TableCell>}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
