import type { Metadata } from "next";

import { ApplyLeaveDialog } from "@/components/leave/apply-leave-dialog";
import { BalanceCards } from "@/components/leave/balance-cards";
import { CancelRequestButton } from "@/components/leave/request-actions";
import { RequestsTable } from "@/components/leave/requests-table";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api/client";
import type { LeaveBalance, LeaveRequest } from "@/lib/api/types";
import { requireRole } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Leave" };

export default async function LeavePage(props: PageProps<"/leave">) {
  const user = await requireRole("EMPLOYEE", "MANAGER", "HR_ADMIN");
  const [query, balances, requests] = await Promise.all([
    props.searchParams,
    apiFetch<LeaveBalance[]>("/leave/balances"),
    apiFetch<LeaveRequest[]>("/leave/requests", { query: { scope: "mine" } }),
  ]);

  // Mirrors BRD 4.1: employees cancel pending only; managers and HR may cancel approved too.
  const cancellable = (r: LeaveRequest) =>
    r.status === "PENDING" || (r.status === "APPROVED" && user.role !== "EMPLOYEE");

  return (
    <>
      <PageHeader
        title="Leave"
        description="Your balances, requests and applications."
        actions={<ApplyLeaveDialog balances={balances} defaultOpen={query.apply === "1"} />}
      />
      <section className="mb-8" aria-label="Leave balances">
        <BalanceCards balances={balances} />
      </section>
      <Card>
        <CardHeader>
          <CardTitle>My requests</CardTitle>
          <CardDescription>Most recent first</CardDescription>
        </CardHeader>
        <CardContent>
          <RequestsTable
            requests={requests}
            emptyDescription="Requests you submit will appear here."
            renderActions={(r) => (cancellable(r) ? <CancelRequestButton requestId={r.id} /> : null)}
          />
        </CardContent>
      </Card>
    </>
  );
}
