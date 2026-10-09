import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Lock } from "lucide-react";

import { BalanceCards } from "@/components/leave/balance-cards";
import { RequestsTable } from "@/components/leave/requests-table";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmployeeRowActions } from "@/components/team/employee-row-actions";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, apiFetch } from "@/lib/api/client";
import type {
  AttendanceReport,
  EmployeeDetail,
  EmployeeSummary,
  LeaveBalance,
  LeaveRequest,
  Payslip,
} from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";
import { formatCurrency, formatDate, formatMonth, initials } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/navigation";

export const metadata: Metadata = { title: "Employee profile" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ATTENDANCE_ORDER = ["PRESENT", "WFH", "LATE", "ON_LEAVE", "ABSENT"] as const;
const RECENT_REQUESTS = 8;

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

export default async function EmployeeProfilePage(props: PageProps<"/team/[id]">) {
  const user = await requireRole("MANAGER", "HR_ADMIN");
  const { id } = await props.params;
  if (!UUID.test(id)) notFound();

  // The API decides visibility (team for managers, company for HR). A refusal looks the same
  // as a missing record, so we answer both with 404 rather than confirming the ID exists.
  let employee: EmployeeDetail;
  try {
    employee = await apiFetch<EmployeeDetail>(`/employees/${id}`);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 403 || error.status === 404)) notFound();
    throw error;
  }

  const isHr = user.role === "HR_ADMIN";
  const isSelf = employee.id === user.employee_id;
  const leaveScope = isSelf ? "mine" : isHr ? "company" : "team";

  const [balances, requests, attendance, payslips, colleagues] = await Promise.all([
    apiFetch<LeaveBalance[]>("/leave/balances", { query: { employee_id: id } }),
    apiFetch<LeaveRequest[]>("/leave/requests", {
      query: { scope: leaveScope, employee_id: isSelf ? undefined : id },
    }),
    apiFetch<AttendanceReport>("/attendance", { query: { employee_id: id } }),
    // Managers never see their reports' pay (BRD 4.1), so don't even ask.
    isHr || isSelf ? apiFetch<Payslip[]>("/payslips", { query: { employee_id: id } }) : null,
    isHr && !isSelf ? apiFetch<EmployeeSummary[]>("/employees") : null,
  ]);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <Avatar className="size-16">
            <AvatarFallback className="bg-primary/10 text-xl text-primary">
              {initials(employee.full_name)}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">{employee.full_name}</h1>
            <p className="text-sm text-muted-foreground">
              {employee.job_title} · {employee.department}
            </p>
            <div className="flex flex-wrap gap-2">
              {employee.role && <Badge variant="secondary">{ROLE_LABELS[employee.role]}</Badge>}
              {!employee.is_active && <Badge variant="destructive">Inactive</Badge>}
              {isSelf && <Badge variant="outline">You</Badge>}
            </div>
          </div>
        </div>
        {colleagues && (
          <EmployeeRowActions employee={employee} employees={colleagues} trigger="button" />
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Employment</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-6 sm:grid-cols-2">
              <Field label="Employee ID">
                <span className="tabular">{employee.employee_code}</span>
              </Field>
              <Field label="Email">{employee.email}</Field>
              <Field label="Department">{employee.department}</Field>
              <Field label="Reports to">
                {employee.manager_id && employee.manager_name ? (
                  <Link
                    href={`/team/${employee.manager_id}`}
                    className="underline-offset-4 hover:underline"
                  >
                    {employee.manager_name}
                  </Link>
                ) : (
                  "—"
                )}
              </Field>
              <Field label="Joined">{formatDate(employee.join_date)}</Field>
              <Field label="Monthly salary">
                {employee.salary_masked ? (
                  <span className="inline-flex items-center gap-1 text-muted-foreground">
                    <Lock className="size-3" aria-hidden /> Restricted
                  </span>
                ) : (
                  <span className="tabular">{formatCurrency(employee.salary)}</span>
                )}
              </Field>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Attendance this month</CardTitle>
            <CardAction>
              <Button asChild variant="ghost" size="sm">
                <Link href={`/attendance?employee=${employee.id}`}>Full log</Link>
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {ATTENDANCE_ORDER.map((status) => (
                <li key={status} className="flex items-center justify-between">
                  <StatusBadge status={status} />
                  <span className="tabular font-medium">{attendance.summary[status] ?? 0}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <section className="mt-8 space-y-4" aria-labelledby="leave-heading">
        <h2 id="leave-heading" className="text-lg font-semibold tracking-tight">
          Leave
        </h2>
        {balances.length > 0 ? (
          <BalanceCards balances={balances} />
        ) : (
          <Card>
            <CardContent>
              <EmptyState title="No leave allocation for this year" />
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader>
            <CardTitle>Recent requests</CardTitle>
            {requests.length > RECENT_REQUESTS && (
              <CardDescription>
                Showing the latest {RECENT_REQUESTS} of {requests.length}.
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <RequestsTable
              requests={requests.slice(0, RECENT_REQUESTS)}
              emptyTitle="No leave requests yet"
            />
          </CardContent>
        </Card>
      </section>

      {payslips && (
        <section className="mt-8 space-y-4" aria-labelledby="pay-heading">
          <h2 id="pay-heading" className="text-lg font-semibold tracking-tight">
            Payslips
          </h2>
          <Card>
            <CardContent>
              {payslips.length === 0 ? (
                <EmptyState title="No payslips yet" />
              ) : (
                <ul className="divide-y">
                  {payslips.slice(0, 3).map((p) => (
                    <li key={p.id} className="flex items-center justify-between py-3 text-sm">
                      <span>{formatMonth(p.month)}</span>
                      <span className="text-muted-foreground">
                        Net <span className="tabular font-medium text-foreground">{formatCurrency(p.net)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
            {isHr && (
              <CardContent className="pt-0">
                <Button asChild variant="ghost" size="sm" className="-ml-2">
                  <Link href={`/payslips?employee=${employee.id}`}>All payslips</Link>
                </Button>
              </CardContent>
            )}
          </Card>
        </section>
      )}
    </>
  );
}
