import type { Metadata } from "next";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { AuditDetails } from "@/components/audit/audit-details";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api/client";
import type { AuditPage } from "@/lib/api/types";
import { ACTIONS, OUTCOME_LABELS, actionLabel, isDenied, sourceLabel, summary } from "@/lib/audit-format";
import { requireRole } from "@/lib/auth/session";
import { formatDateTime } from "@/lib/format";

export const metadata: Metadata = { title: "Audit Log" };

const PAGE_SIZE = 25;
const SELECT_CLASS =
  "h-9 w-full rounded-lg border border-input bg-card px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-white/[0.06]";

function param(value: string | string[] | undefined): string {
  return typeof value === "string" ? value : "";
}

export default async function AuditLogPage(props: PageProps<"/admin/audit">) {
  const user = await requireRole("HR_ADMIN", "PLATFORM_ADMIN");
  const query = await props.searchParams;
  const filters = {
    outcome: param(query.outcome),
    tool: param(query.tool),
    since: param(query.since),
  };
  const page = Math.max(1, Number(param(query.page)) || 1);

  const data = await apiFetch<AuditPage>("/audit", {
    query: {
      outcome: filters.outcome,
      tool: filters.tool,
      since: filters.since ? `${filters.since}T00:00:00Z` : undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    },
  });
  const metadataOnly = user.role === "PLATFORM_ADMIN";
  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const pageHref = (p: number) =>
    `/admin/audit?${new URLSearchParams({ ...filters, page: String(p) }).toString()}`;
  const filtered = Boolean(filters.outcome || filters.tool || filters.since);

  return (
    <>
      <PageHeader
        title="Audit Log"
        description={
          metadataOnly
            ? "Activity across all organisations. Names, messages and record details are never shown at platform level."
            : `Every action and refused request in ${user.tenant_name}. Salaries and ID numbers are hidden before storage.`
        }
      />

      <Card className="mb-6">
        <CardContent>
          <form className="grid gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end">
            <div className="space-y-2">
              <Label htmlFor="outcome">Outcome</Label>
              <select id="outcome" name="outcome" defaultValue={filters.outcome} className={SELECT_CLASS}>
                <option value="">All outcomes</option>
                {Object.entries(OUTCOME_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool">Action</Label>
              <select id="tool" name="tool" defaultValue={filters.tool} className={SELECT_CLASS}>
                <option value="">All actions</option>
                {Object.entries(ACTIONS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="since">From date</Label>
              <Input id="since" name="since" type="date" defaultValue={filters.since} />
            </div>
            <div className="flex gap-2">
              <Button type="submit">Apply</Button>
              {filtered && (
                <Button asChild variant="ghost">
                  <Link href="/admin/audit">Clear</Link>
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-primary" aria-hidden /> Activity
            <span className="tabular text-sm font-normal text-muted-foreground">
              {data.total.toLocaleString("en-GB")} {data.total === 1 ? "entry" : "entries"}
            </span>
          </CardTitle>
          <CardDescription>Records are permanent: they can&apos;t be edited or deleted.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.items.length === 0 ? (
            <EmptyState
              title={filtered ? "No activity matches these filters" : "No activity yet"}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>When</TableHead>
                    {metadataOnly ? (
                      <TableHead>Organisation</TableHead>
                    ) : (
                      <TableHead>Who</TableHead>
                    )}
                    <TableHead>Action</TableHead>
                    {!metadataOnly && <TableHead>Employee</TableHead>}
                    <TableHead>Outcome</TableHead>
                    {metadataOnly ? (
                      <TableHead>Source</TableHead>
                    ) : (
                      <TableHead>Details</TableHead>
                    )}
                    {!metadataOnly && (
                      <TableHead className="w-20">
                        <span className="sr-only">More</span>
                      </TableHead>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((e) => {
                    const line = metadataOnly ? "" : summary(e);
                    return (
                      <TableRow key={e.id}>
                        <TableCell className="whitespace-nowrap text-muted-foreground">
                          {formatDateTime(e.ts)}
                        </TableCell>
                        {metadataOnly ? (
                          <TableCell className="text-muted-foreground">
                            {e.tenant_id ? `Org ${e.tenant_id.slice(0, 8)}` : "Platform"}
                          </TableCell>
                        ) : (
                          <TableCell className="whitespace-nowrap font-medium">
                            {e.actor_name ?? "Unknown user"}
                          </TableCell>
                        )}
                        <TableCell className="whitespace-nowrap">{actionLabel(e)}</TableCell>
                        {!metadataOnly && (
                          <TableCell className="whitespace-nowrap text-muted-foreground">
                            {e.subject_name ?? "—"}
                          </TableCell>
                        )}
                        <TableCell>
                          <StatusBadge status={e.outcome} label={OUTCOME_LABELS[e.outcome]} />
                        </TableCell>
                        {metadataOnly ? (
                          <TableCell className="text-muted-foreground">{sourceLabel(e.channel)}</TableCell>
                        ) : (
                          <TableCell
                            className={`max-w-xs truncate ${isDenied(e) ? "text-foreground/80" : "text-muted-foreground"}`}
                            title={line}
                          >
                            {line || "—"}
                          </TableCell>
                        )}
                        {!metadataOnly && (
                          <TableCell className="text-right">
                            <AuditDetails entry={e} />
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
          {pages > 1 && (
            <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pagination">
              <span className="text-muted-foreground">
                Page {page} of {pages}
              </span>
              <div className="flex gap-2">
                {page > 1 && (
                  <Button asChild variant="outline" size="sm">
                    <Link href={pageHref(page - 1)}>Previous</Link>
                  </Button>
                )}
                {page < pages && (
                  <Button asChild variant="outline" size="sm">
                    <Link href={pageHref(page + 1)}>Next</Link>
                  </Button>
                )}
              </div>
            </nav>
          )}
        </CardContent>
      </Card>
    </>
  );
}
