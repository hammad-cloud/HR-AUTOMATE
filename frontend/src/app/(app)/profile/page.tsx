import type { Metadata } from "next";
import { Lock } from "lucide-react";

import { ChangePasswordForm } from "@/components/profile/change-password-form";
import { PageHeader } from "@/components/shared/page-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiFetch } from "@/lib/api/client";
import type { EmployeeDetail } from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";
import { formatCurrency, formatDate, initials } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/navigation";

export const metadata: Metadata = { title: "My Profile" };

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

export default async function ProfilePage() {
  const user = await requireRole("EMPLOYEE", "MANAGER", "HR_ADMIN");
  const me = await apiFetch<EmployeeDetail>("/employees/me");

  return (
    <>
      <PageHeader title="My Profile" description="Your personal and employment details." />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-6 text-center">
            <Avatar className="size-20">
              <AvatarFallback className="bg-primary/10 text-2xl text-primary">
                {initials(me.full_name)}
              </AvatarFallback>
            </Avatar>
            <div>
              <p className="text-lg font-semibold">{me.full_name}</p>
              <p className="text-sm text-muted-foreground">{me.job_title}</p>
            </div>
            <Badge variant="secondary">{ROLE_LABELS[user.role]}</Badge>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Employment</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-6 sm:grid-cols-2">
              <Field label="Employee ID">{me.employee_code}</Field>
              <Field label="Email">{me.email}</Field>
              <Field label="Department">{me.department}</Field>
              <Field label="Reports to">{me.manager_name ?? "—"}</Field>
              <Field label="Joined">{formatDate(me.join_date)}</Field>
              <Field label="Organisation">{user.tenant_name}</Field>
              <Field label="Monthly salary">
                {me.salary_masked ? (
                  <span className="inline-flex items-center gap-1 text-muted-foreground">
                    <Lock className="size-3" aria-hidden /> Restricted
                  </span>
                ) : (
                  <span className="tabular">{formatCurrency(me.salary)}</span>
                )}
              </Field>
            </dl>
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Password</CardTitle>
            <CardDescription>
              If HR gave you a temporary password, replace it with one only you know.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChangePasswordForm />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
