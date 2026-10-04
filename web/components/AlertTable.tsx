import Link from "next/link";

import { CredentialEmailButton } from "@/components/CredentialEmailButton";
import { ThresholdBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Alert, Credential } from "@/lib/api";
import { sentAt } from "@/lib/format";

/**
 * Outbox rows, one per recipient. Alerts only carry `credential_id`, so the associate and credential
 * come from `credentials`; a credential missing there (e.g. renewed since the alert) shows its id.
 */
export function AlertTable({ alerts, credentials }: { alerts: Alert[]; credentials: Map<number, Credential> }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Sent</TableHead>
          <TableHead>Threshold</TableHead>
          <TableHead>Associate</TableHead>
          <TableHead>Credential</TableHead>
          <TableHead>Recipient</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {alerts.map((a) => {
          const c = credentials.get(a.credential_id);
          return (
            <TableRow key={a.id}>
              <TableCell className="tabular-nums">{sentAt(a.sent_at)}</TableCell>
              <TableCell>
                <ThresholdBadge threshold={a.threshold} />
              </TableCell>
              <TableCell>
                {c ? (
                  <>
                    <Link href={`/associates/${c.associate_id}`} className="font-medium hover:underline">
                      {c.associate_name}
                    </Link>
                    <div className="text-xs text-muted-foreground">
                      {c.department} · {c.facility}
                    </div>
                  </>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {c ? (
                  <>
                    {c.credential_type}
                    <div className="text-xs text-muted-foreground">{c.issuing_source}</div>
                  </>
                ) : (
                  <span className="text-muted-foreground">Credential #{a.credential_id}</span>
                )}
              </TableCell>
              <TableCell>
                {a.sent_to}
                <div className="text-xs text-muted-foreground">{a.channel === "email" ? "Emailed" : "Outbox only"}</div>
              </TableCell>
              <TableCell>
                {c && a.sent_to === c.manager_email && <CredentialEmailButton credential={c} />}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
