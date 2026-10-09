import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Text labels always accompany colour, so status is never conveyed by colour alone (NFR-12).
const STYLES: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-900 dark:bg-amber-500/15 dark:text-amber-300",
  APPROVED: "bg-emerald-100 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-300",
  SUCCESS: "bg-emerald-100 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-300",
  PRESENT: "bg-emerald-100 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-300",
  REJECTED: "bg-red-100 text-red-900 dark:bg-red-500/15 dark:text-red-300",
  PERMISSION_DENIED: "bg-red-100 text-red-900 dark:bg-red-500/15 dark:text-red-300",
  ABSENT: "bg-red-100 text-red-900 dark:bg-red-500/15 dark:text-red-300",
  LATE: "bg-orange-100 text-orange-900 dark:bg-orange-500/15 dark:text-orange-300",
  WFH: "bg-sky-100 text-sky-900 dark:bg-sky-500/15 dark:text-sky-300",
  ON_LEAVE: "bg-violet-100 text-violet-900 dark:bg-violet-500/15 dark:text-violet-300",
  CANCELLED: "bg-muted text-muted-foreground",
  ERROR: "bg-red-100 text-red-900 dark:bg-red-500/15 dark:text-red-300",
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const fallback = status.replaceAll("_", " ").toLowerCase();
  return (
    <Badge variant="secondary" className={cn(!label && "capitalize", STYLES[status])}>
      {label ?? (status === "WFH" ? "WFH" : fallback)}
    </Badge>
  );
}
