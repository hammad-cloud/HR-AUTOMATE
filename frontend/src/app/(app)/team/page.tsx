import type { Metadata } from "next";
import Link from "next/link";
import { Search } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { AddEmployeeDialog } from "@/components/team/add-employee-dialog";
import { EmployeeRowActions } from "@/components/team/employee-row-actions";
import { PageHeader } from "@/components/shared/page-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api/client";
import type { EmployeeSummary } from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";
import { initials } from "@/lib/format";

export async function generateMetadata(): Promise<Metadata> {
  const user = await requireRole("MANAGER", "HR_ADMIN");
  return { title: user.role === "HR_ADMIN" ? "People" : "My Team" };
}

export default async function TeamPage(props: PageProps<"/team">) {
  const user = await requireRole("MANAGER", "HR_ADMIN");
  const query = await props.searchParams;
  const search = typeof query.q === "string" ? query.q.slice(0, 80) : "";
  const isHr = user.role === "HR_ADMIN";
  const status = isHr && query.status === "inactive" ? "inactive" : "active";
  const people = await apiFetch<EmployeeSummary[]>("/employees", { query: { search, status } });
  // Forms need every active colleague (managers, departments), not just the visible rows.
  const everyone =
    isHr && (search || status === "inactive")
      ? await apiFetch<EmployeeSummary[]>("/employees")
      : people;
  const departments = new Set(people.map((p) => p.department)).size;
  const statusHref = (s: string) => `/team?${new URLSearchParams({ status: s, ...(search && { q: search }) })}`;

  return (
    <>
      <PageHeader
        title={isHr ? "People" : "My Team"}
        description={
          !isHr
            ? `You and your ${Math.max(people.length - 1, 0)} direct reports.`
            : status === "inactive"
              ? `${people.length} former employees. Their records are kept for history and audit.`
              : `${people.length} employees across ${departments} departments.`
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {isHr && (
              <nav className="flex rounded-lg bg-muted p-0.5" aria-label="Employee status">
                {(["active", "inactive"] as const).map((s) => (
                  <Button
                    key={s}
                    asChild
                    size="sm"
                    variant={status === s ? "secondary" : "ghost"}
                    className={status === s ? "bg-background shadow-sm" : undefined}
                  >
                    <Link href={statusHref(s)} aria-current={status === s ? "page" : undefined}>
                      {s === "active" ? "Active" : "Inactive"}
                    </Link>
                  </Button>
                ))}
              </nav>
            )}
            <form className="relative" role="search">
              {status === "inactive" && <input type="hidden" name="status" value="inactive" />}
              <Search
                className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                name="q"
                defaultValue={search}
                placeholder="Search by name"
                className="w-60 pl-8"
                aria-label="Search employees"
              />
            </form>
            {isHr && <AddEmployeeDialog employees={everyone} />}
          </div>
        }
      />
      <Card>
        <CardContent>
          {people.length === 0 ? (
            <EmptyState
              title={status === "inactive" && !search ? "No former employees" : "No matching employees"}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Job title</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Employee ID</TableHead>
                  <TableHead className="text-right">Records</TableHead>
                  {isHr && (
                    <TableHead className="w-12">
                      <span className="sr-only">Actions</span>
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {people.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="size-8">
                          <AvatarFallback className="text-xs">{initials(p.full_name)}</AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium">
                            <Link
                              href={`/team/${p.id}`}
                              className="underline-offset-4 hover:underline"
                            >
                              {p.full_name}
                            </Link>
                            {p.id === user.employee_id && (
                              <Badge variant="outline" className="ml-2">
                                You
                              </Badge>
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground">{p.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{p.job_title}</TableCell>
                    <TableCell>{p.department}</TableCell>
                    <TableCell className="tabular text-muted-foreground">{p.employee_code}</TableCell>
                    <TableCell className="text-right">
                      <Button asChild size="sm" variant="ghost">
                        <Link href={`/attendance?employee=${p.id}`}>Attendance</Link>
                      </Button>
                    </TableCell>
                    {isHr && (
                      <TableCell className="text-right">
                        {p.id !== user.employee_id && (
                          <EmployeeRowActions employee={p} employees={everyone} />
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
