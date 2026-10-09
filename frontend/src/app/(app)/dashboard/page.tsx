import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  CalendarClock,
  ClipboardCheck,
  ScrollText,
  ShieldAlert,
  Users,
} from "lucide-react";

import { BalanceCards } from "@/components/leave/balance-cards";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiFetch } from "@/lib/api/client";
import type { AttendanceStatus, DashboardStats } from "@/lib/api/types";
import { requireUser } from "@/lib/auth/session";
import { routesFor } from "@/lib/navigation";

export const metadata: Metadata = { title: "Dashboard" };

// Same hues as StatusBadge, so a status reads the same everywhere.
const ATTENDANCE: { status: AttendanceStatus; label: string; bar: string }[] = [
  { status: "PRESENT", label: "Present", bar: "bg-emerald-500" },
  { status: "WFH", label: "Work from home", bar: "bg-sky-500" },
  { status: "LATE", label: "Late", bar: "bg-orange-400" },
  { status: "ON_LEAVE", label: "On leave", bar: "bg-violet-500" },
  { status: "ABSENT", label: "Absent", bar: "bg-red-500" },
];

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default async function DashboardPage(props: PageProps<"/dashboard">) {
  const [user, query] = await Promise.all([requireUser(), props.searchParams]);
  const denied = query.denied === "1";
  const firstName = user.full_name.split(" ")[0];

  if (user.role === "PLATFORM_ADMIN") {
    return (
      <>
        <PageHeader
          title={`${greeting()}, ${firstName}`}
          description="Platform operations across all tenants."
        />
        <Card>
          <CardHeader>
            <CardTitle>No HR data at platform level</CardTitle>
            <CardDescription>
              Platform admins can review audit metadata across tenants but never see employee
              records, salaries or message content. This is enforced by the database.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/admin/audit">
                Open audit log <ArrowRight aria-hidden />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </>
    );
  }

  const stats = await apiFetch<DashboardStats>("/dashboard");
  const attendanceTotal = Object.values(stats.attendance_this_month).reduce(
    (sum, n) => sum + (n ?? 0),
    0,
  );
  const quickLinks = routesFor(user.role).filter((r) => r.href !== "/dashboard");

  return (
    <>
      <PageHeader
        title={`${greeting()}, ${firstName}`}
        description={`${user.job_title} · ${user.department} · ${user.tenant_name}`}
        actions={
          <Button asChild>
            <Link href="/leave?apply=1">Apply for leave</Link>
          </Button>
        }
      />

      {denied && (
        <Alert variant="destructive" className="mb-6">
          <ShieldAlert aria-hidden />
          <AlertTitle>Access restricted</AlertTitle>
          <AlertDescription>Your role does not have access to that page.</AlertDescription>
        </Alert>
      )}

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="My pending requests"
          value={stats.pending_my_requests}
          icon={CalendarClock}
          hint="Awaiting a decision"
        />
        {user.role !== "EMPLOYEE" && (
          <StatCard
            label="Awaiting my approval"
            value={stats.pending_my_approvals}
            icon={ClipboardCheck}
            hint={user.role === "HR_ADMIN" ? "Company-wide" : "From your direct reports"}
          />
        )}
        {stats.team_size !== null && (
          <StatCard label="Direct reports" value={stats.team_size} icon={Users} />
        )}
        {stats.headcount !== null && (
          <StatCard label="Active headcount" value={stats.headcount} icon={Users} />
        )}
      </div>

      <section className="mb-8 space-y-4" aria-labelledby="balances">
        <h2 id="balances" className="text-lg font-semibold">
          Leave balance {new Date().getFullYear()}
        </h2>
        <BalanceCards balances={stats.leave_balances} />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Attendance this month</CardTitle>
            <CardDescription>
              {attendanceTotal === 0
                ? "No working days recorded yet this month."
                : `${attendanceTotal} working day${attendanceTotal === 1 ? "" : "s"} recorded so far`}
            </CardDescription>
            <CardAction>
              <Button asChild variant="ghost" size="sm">
                <Link href="/attendance">View log</Link>
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-5">
            <div
              className="flex h-2.5 overflow-hidden rounded-full bg-muted"
              role="img"
              aria-label={ATTENDANCE.map(
                (a) => `${stats.attendance_this_month[a.status] ?? 0} ${a.label}`,
              ).join(", ")}
            >
              {ATTENDANCE.map((a) => {
                const count = stats.attendance_this_month[a.status] ?? 0;
                return attendanceTotal > 0 && count > 0 ? (
                  <div
                    key={a.status}
                    className={a.bar}
                    style={{ width: `${(count / attendanceTotal) * 100}%` }}
                  />
                ) : null;
              })}
            </div>
            <ul className="divide-y">
              {ATTENDANCE.map((a) => (
                <li key={a.status} className="flex items-center justify-between py-2.5 text-sm">
                  <span className="flex items-center gap-2.5">
                    <span className={`size-2.5 rounded-full ${a.bar}`} aria-hidden />
                    {a.label}
                  </span>
                  <span className="tabular font-semibold">
                    {stats.attendance_this_month[a.status] ?? 0}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick links</CardTitle>
            <CardDescription>Everything your role can access</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            {quickLinks.map((route) => (
              <Link
                key={route.href}
                href={route.href}
                className="group flex items-center justify-between rounded-lg border px-3 py-2 text-sm hover:bg-muted"
              >
                <span>
                  <span className="block font-medium">{route.label}</span>
                  <span className="block text-xs text-muted-foreground">{route.description}</span>
                </span>
                {route.icon === "audit" ? (
                  <ScrollText className="size-4 text-muted-foreground" aria-hidden />
                ) : (
                  <ArrowRight
                    className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                )}
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
