"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatMonth } from "@/lib/format";

function shift(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** Month navigation stored in the URL (?month=YYYY-MM) so views are shareable and deep-linkable. */
export function MonthPicker({ month, max }: { month: string; max: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  function go(next: string) {
    const query = new URLSearchParams(params);
    query.set("month", next);
    router.push(`${pathname}?${query.toString()}`);
  }

  return (
    <div className="flex items-center gap-1 rounded-lg border p-1">
      <Button variant="ghost" size="icon-sm" onClick={() => go(shift(month, -1))} aria-label="Previous month">
        <ChevronLeft />
      </Button>
      <span className="min-w-36 text-center text-sm font-medium" aria-live="polite">
        {formatMonth(month)}
      </span>
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={() => go(shift(month, 1))}
        disabled={month >= max}
        aria-label="Next month"
      >
        <ChevronRight />
      </Button>
    </div>
  );
}
