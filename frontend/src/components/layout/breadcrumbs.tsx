"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

import type { AppRoute } from "@/lib/navigation";

import { isActive } from "./nav-links";

/** "Acme Corp › People › Profile": where you are, derived from the route registry. */
export function Breadcrumbs({ routes, org }: { routes: AppRoute[]; org: string }) {
  const pathname = usePathname();
  const hrefs = routes.map((r) => r.href);
  const section = routes.find((r) => isActive(pathname, r.href, hrefs));
  const isDetail = section !== undefined && pathname !== section.href;

  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        <li className="hidden truncate text-muted-foreground sm:block">{org}</li>
        {section && (
          <>
            <li aria-hidden className="hidden text-muted-foreground/60 sm:block">
              <ChevronRight className="size-3.5" />
            </li>
            <li className="truncate">
              {isDetail ? (
                <Link href={section.href} className="text-muted-foreground hover:text-foreground">
                  {section.label}
                </Link>
              ) : (
                <span className="font-medium" aria-current="page">
                  {section.label}
                </span>
              )}
            </li>
          </>
        )}
        {isDetail && (
          <>
            <li aria-hidden className="text-muted-foreground/60">
              <ChevronRight className="size-3.5" />
            </li>
            <li className="truncate font-medium" aria-current="page">
              Details
            </li>
          </>
        )}
      </ol>
    </nav>
  );
}
