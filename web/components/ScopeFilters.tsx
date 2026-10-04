"use client";

import { useQuery } from "@tanstack/react-query";

import { useDemoManager, useHrScope, useRole } from "@/components/Providers";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, type Scope } from "@/lib/api";

const ALL = "all";

function Filter({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}) {
  const items = [{ value: ALL, label: `All ${label}` }, ...options.map((o) => ({ value: o, label: o }))];
  return (
    <Select items={items} value={value ?? ALL} onValueChange={(v) => onChange(!v || v === ALL ? undefined : v)}>
      <SelectTrigger aria-label={label} className="max-w-full min-w-44">
        {/* Every label sits invisibly in the same grid cell as the value, so the trigger (and the list, which matches
            its width) fits the longest option whatever is picked; on a narrow row it shrinks and the value truncates. */}
        <span className="grid min-w-0 flex-1 overflow-hidden">
          {items.map((item) => (
            <span key={item.value} aria-hidden className="invisible col-start-1 row-start-1 h-0 whitespace-nowrap">
              {item.label}
            </span>
          ))}
          <SelectValue className="col-start-1 row-start-1 block truncate" />
        </span>
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false} className="max-w-(--available-width)">
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** The scope for the current role: a manager sees their own team, HR filters across everyone. */
export function useScope(): { scope: Scope; filters: React.ReactNode } {
  const { role } = useRole();
  const [picked, setPicked] = useHrScope();
  const options = useQuery({ queryKey: ["filters"], queryFn: api.filters, staleTime: Infinity });
  const demo = useDemoManager();

  if (role === "manager") {
    return {
      scope: { manager: demo.manager },
      filters: <p className="text-sm text-muted-foreground">Your team: {demo.team}</p>,
    };
  }
  const set = (key: keyof Scope) => (value: string | undefined) => setPicked((p) => ({ ...p, [key]: value }));
  return {
    scope: picked,
    filters: (
      <div className="flex flex-wrap gap-2">
        <Filter label="facilities" options={options.data?.facilities ?? []} value={picked.facility} onChange={set("facility")} />
        <Filter label="departments" options={options.data?.departments ?? []} value={picked.department} onChange={set("department")} />
        <Filter label="managers" options={options.data?.managers ?? []} value={picked.manager} onChange={set("manager")} />
      </div>
    ),
  };
}
