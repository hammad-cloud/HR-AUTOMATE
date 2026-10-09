"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CalendarCheck,
  CalendarDays,
  ClipboardCheck,
  LayoutDashboard,
  ReceiptText,
  ScrollText,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { AppRoute } from "@/lib/navigation";
import { cn } from "@/lib/utils";

const ICONS: Record<AppRoute["icon"], LucideIcon> = {
  dashboard: LayoutDashboard,
  profile: UserRound,
  leave: CalendarDays,
  approvals: ClipboardCheck,
  attendance: CalendarCheck,
  payslips: ReceiptText,
  team: Users,
  audit: ScrollText,
};

export function isActive(pathname: string, href: string, allHrefs: string[]): boolean {
  if (pathname === href) return true;
  // Highlight the most specific match only (/leave vs /leave/approvals).
  const deeper = allHrefs.some((h) => h !== href && h.startsWith(href) && pathname.startsWith(h));
  return pathname.startsWith(`${href}/`) && !deeper;
}

/** Navigation for the navy sidebar rail (desktop and the mobile sheet). */
export function NavLinks({ routes, onNavigate }: { routes: AppRoute[]; onNavigate?: () => void }) {
  const pathname = usePathname();
  const hrefs = routes.map((r) => r.href);
  const sections = [...new Set(routes.map((r) => r.section))];

  return (
    <nav aria-label="Main" className="space-y-6">
      {sections.map((section) => (
        <div key={section} className="space-y-0.5">
          <p className="px-3 pb-1.5 text-[11px] font-semibold tracking-wider text-sidebar-muted uppercase">
            {section}
          </p>
          {routes
            .filter((r) => r.section === section)
            .map((route) => {
              const Icon = ICONS[route.icon];
              const active = isActive(pathname, route.href, hrefs);
              return (
                <Link
                  key={route.href}
                  href={route.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                    active
                      ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-indigo-300"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                  )}
                >
                  <Icon className={cn("size-4", active ? "text-indigo-200" : "opacity-80")} aria-hidden />
                  {route.label}
                </Link>
              );
            })}
        </div>
      ))}
    </nav>
  );
}
