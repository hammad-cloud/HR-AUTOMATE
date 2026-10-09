import { Brand } from "@/components/layout/brand";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { MobileNav } from "@/components/layout/mobile-nav";
import { NavLinks } from "@/components/layout/nav-links";
import { UserMenu } from "@/components/layout/user-menu";
import { requireUser } from "@/lib/auth/session";
import { routesFor } from "@/lib/navigation";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  const routes = routesFor(user.role);
  const org = user.tenant_name ?? "Platform";

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-3 py-5 text-sidebar-foreground lg:flex">
        <div className="mb-8 px-1">
          <Brand />
        </div>
        <div className="flex-1 overflow-y-auto">
          <NavLinks routes={routes} />
        </div>
        <div className="mt-4 flex items-center gap-3 rounded-lg bg-sidebar-accent px-3 py-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-white/10 text-xs font-semibold text-white">
            {org.slice(0, 2).toUpperCase()}
          </span>
          <div className="min-w-0 text-xs">
            <p className="truncate font-medium text-white">{org}</p>
            <p className="truncate text-sidebar-muted">Data scoped to your role</p>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b bg-card px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <MobileNav routes={routes} />
            <Breadcrumbs routes={routes} org={org} />
          </div>
          <UserMenu user={user} />
        </header>
        <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
