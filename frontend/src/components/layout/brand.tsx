import Link from "next/link";
import { Building2 } from "lucide-react";

/** Logo lock-up for the navy sidebar rail. */
export function Brand() {
  return (
    <Link
      href="/dashboard"
      className="flex items-center gap-2.5 rounded-md px-2 font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
    >
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm ring-1 ring-white/10">
        <Building2 className="size-4" aria-hidden />
      </span>
      <span className="tracking-tight">HR Copilot</span>
    </Link>
  );
}
