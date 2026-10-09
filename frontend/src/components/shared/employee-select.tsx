"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { EmployeeSummary } from "@/lib/api/types";

/** Lets managers / HR switch whose records they view. The API still authorizes each request. */
export function EmployeeSelect({
  employees,
  value,
}: {
  employees: EmployeeSummary[];
  value: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  return (
    <Select
      value={value}
      onValueChange={(id) => {
        const query = new URLSearchParams(params);
        query.set("employee", id);
        router.push(`${pathname}?${query.toString()}`);
      }}
    >
      <SelectTrigger className="w-60" aria-label="Employee">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {employees.map((e) => (
          <SelectItem key={e.id} value={e.id}>
            {e.full_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
