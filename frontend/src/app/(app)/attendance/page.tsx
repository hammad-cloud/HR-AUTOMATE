import type { Metadata } from "next";

import { EmployeeSelect } from "@/components/shared/employee-select";
import { EmptyState } from "@/components/shared/empty-state";
import { MonthPicker } from "@/components/shared/month-picker";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api/client";
import type { AttendanceReport, EmployeeSummary } from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = { title: "Attendance" };

const SUMMARY_ORDER = ["PRESENT", "WFH", "LATE", "ON_LEAVE", "ABSENT"] as const;

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default async function AttendancePage(props: PageProps<"/attendance">) {
  const user = await requireRole("EMPLOYEE", "MANAGER", "HR_ADMIN");
  const query = await props.searchParams;
  const max = currentMonth();
  const month = typeof query.month === "string" && /^\d{4}-\d{2}$/.test(query.month) ? query.month : max;
  const employeeId =
    typeof query.employee === "string" ? query.employee : (user.employee_id ?? undefined);

  const [report, people] = await Promise.all([
    apiFetch<AttendanceReport>("/attendance", { query: { month, employee_id: employeeId } }),
    user.role === "EMPLOYEE" ? Promise.resolve([]) : apiFetch<EmployeeSummary[]>("/employees"),
  ]);

  return (
    <>
      <PageHeader
        title="Attendance"
        description={`Daily check-in records for ${report.employee.full_name}.`}
        actions={
          <>
            {people.length > 1 && (
              <EmployeeSelect employees={people} value={report.employee.id} />
            )}
            <MonthPicker month={month} max={max} />
          </>
        }
      />
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {SUMMARY_ORDER.map((status) => (
          <Card key={status} size="sm">
            <CardContent className="space-y-2">
              <StatusBadge status={status} />
              <p className="tabular text-2xl font-semibold">{report.summary[status] ?? 0}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Daily log</CardTitle>
        </CardHeader>
        <CardContent>
          {report.records.length === 0 ? (
            <EmptyState title="No attendance records" description="Nothing recorded for this month." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Check in</TableHead>
                  <TableHead>Check out</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.records.map((r) => (
                  <TableRow key={r.date}>
                    <TableCell>{formatDate(r.date, { weekday: "short", year: undefined })}</TableCell>
                    <TableCell className="tabular">{r.check_in?.slice(0, 5) ?? "—"}</TableCell>
                    <TableCell className="tabular">{r.check_out?.slice(0, 5) ?? "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={r.status} />
                    </TableCell>
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
