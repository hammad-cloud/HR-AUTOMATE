import type { Metadata } from "next";
import { ReceiptText } from "lucide-react";

import { EmployeeSelect } from "@/components/shared/employee-select";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { apiFetch } from "@/lib/api/client";
import type { EmployeeSummary, Payslip } from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";
import { formatCurrency, formatMonth } from "@/lib/format";

export const metadata: Metadata = { title: "Payslips" };

export default async function PayslipsPage(props: PageProps<"/payslips">) {
  const user = await requireRole("EMPLOYEE", "MANAGER", "HR_ADMIN");
  const query = await props.searchParams;
  // Only HR admins may view other people's pay (BRD 4.1); managers see their own only.
  const canPickEmployee = user.role === "HR_ADMIN";
  const employeeId =
    canPickEmployee && typeof query.employee === "string"
      ? query.employee
      : (user.employee_id ?? undefined);

  const [payslips, people] = await Promise.all([
    apiFetch<Payslip[]>("/payslips", { query: { employee_id: employeeId } }),
    canPickEmployee ? apiFetch<EmployeeSummary[]>("/employees") : Promise.resolve([]),
  ]);

  return (
    <>
      <PageHeader
        title="Payslips"
        description="Monthly salary statements. Amounts in PKR."
        actions={
          canPickEmployee && employeeId ? (
            <EmployeeSelect employees={people} value={employeeId} />
          ) : undefined
        }
      />
      {payslips.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState icon={ReceiptText} title="No payslips yet" />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {payslips.map((p) => (
            <Card key={p.id}>
              <CardHeader>
                <CardTitle>{formatMonth(p.month)}</CardTitle>
                <CardDescription>Salary statement</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Gross pay</span>
                  <span className="tabular">{formatCurrency(p.gross)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Deductions</span>
                  <span className="tabular">−{formatCurrency(p.deductions)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-base font-semibold">
                  <span>Net pay</span>
                  <span className="tabular">{formatCurrency(p.net)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
