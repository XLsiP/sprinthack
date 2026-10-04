import { ArrowDown, ArrowUpDown } from "lucide-react";
import Link from "next/link";

import { NoCredentialsBadge, StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Associate, AssociateQuery } from "@/lib/api";
import { managerName } from "@/lib/format";

export type AssociateSort = NonNullable<AssociateQuery["sort"]>;

/** Header that sorts on the server; only one direction per key, matching the API. */
function SortHead({
  label,
  value,
  sort,
  onSortChange,
  className,
}: {
  label: string;
  value: AssociateSort;
  sort: AssociateSort;
  onSortChange: (sort: AssociateSort) => void;
  className?: string;
}) {
  const active = sort === value;
  const Icon = active ? ArrowDown : ArrowUpDown;
  return (
    <TableHead aria-sort={active ? "ascending" : "none"} className={className}>
      <button
        type="button"
        onClick={() => onSortChange(value)}
        className={`inline-flex items-center gap-1 hover:text-foreground ${active ? "text-foreground" : ""}`}
      >
        {label}
        <Icon className="size-3.5" aria-hidden />
      </button>
    </TableHead>
  );
}

export function AssociateTable({
  associates,
  sort,
  onSortChange,
}: {
  associates: Associate[];
  sort: AssociateSort;
  onSortChange: (sort: AssociateSort) => void;
}) {
  if (associates.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No associates match.</p>;
  }
  // Set widths, with the text columns allowed to wrap, so the columns don't jump as filters change the rows.
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortHead label="Associate" value="name" sort={sort} onSortChange={onSortChange} className="w-[38%]" />
          <TableHead className="w-[34%]">Manager</TableHead>
          <TableHead className="text-right">Credentials</TableHead>
          <SortHead label="Most urgent status" value="urgency" sort={sort} onSortChange={onSortChange} className="w-44" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {associates.map((a) => (
          <TableRow key={a.id}>
            <TableCell className="whitespace-normal">
              <Link href={`/associates/${a.id}`} className="font-medium hover:underline">
                {a.name}
              </Link>
              <div className="text-xs text-muted-foreground">
                {a.role} · {a.department} · {a.facility}
              </div>
            </TableCell>
            <TableCell className="whitespace-normal wrap-anywhere text-muted-foreground" title={a.manager_email}>
              {managerName(a.manager_email)}
            </TableCell>
            <TableCell className="text-right tabular-nums">{a.credential_count}</TableCell>
            <TableCell>{a.worst_status ? <StatusBadge status={a.worst_status} /> : <NoCredentialsBadge />}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
