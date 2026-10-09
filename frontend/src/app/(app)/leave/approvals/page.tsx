import type { Metadata } from "next";
import { ClipboardCheck } from "lucide-react";

import { ApprovalActions } from "@/components/leave/request-actions";
import { RequestsTable } from "@/components/leave/requests-table";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api/client";
import type { LeaveRequest } from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Approvals" };

export default async function ApprovalsPage() {
  const user = await requireRole("MANAGER", "HR_ADMIN");
  const scope = user.role === "HR_ADMIN" ? "company" : "team";
  const [pending, history] = await Promise.all([
    apiFetch<LeaveRequest[]>("/leave/approvals"),
    apiFetch<LeaveRequest[]>("/leave/requests", { query: { scope } }),
  ]);
  const decided = history.filter((r) => r.status !== "PENDING").slice(0, 15);

  return (
    <>
      <PageHeader
        title="Approvals"
        description={
          user.role === "HR_ADMIN"
            ? "Pending leave across the company. You can't decide your own requests."
            : "Pending leave from your direct reports. You can't decide your own requests."
        }
      />
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardCheck className="size-4" aria-hidden /> Awaiting decision
              <span className="tabular text-muted-foreground">({pending.length})</span>
            </CardTitle>
            <CardDescription>Balances are re-checked when you approve.</CardDescription>
          </CardHeader>
          <CardContent>
            <RequestsTable
              requests={pending}
              showEmployee
              showStatus={false}
              emptyTitle="You're all caught up"
              emptyDescription="New requests from your team will appear here."
              renderActions={(r) => <ApprovalActions request={r} />}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recently decided</CardTitle>
            <CardDescription>Approved, rejected and cancelled requests</CardDescription>
          </CardHeader>
          <CardContent>
            <RequestsTable requests={decided} showEmployee emptyTitle="No decisions yet" />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
