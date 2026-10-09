import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { LeaveRequest } from "@/lib/api/types";
import { dateRange, formatDate, formatDays } from "@/lib/format";

export function RequestsTable({
  requests,
  showEmployee = false,
  showStatus = true,
  renderActions,
  emptyTitle = "No leave requests",
  emptyDescription,
}: {
  requests: LeaveRequest[];
  showEmployee?: boolean;
  /** Off where every row has the same status (e.g. the pending approvals queue). */
  showStatus?: boolean;
  renderActions?: (request: LeaveRequest) => React.ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  if (requests.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {showEmployee && <TableHead>Employee</TableHead>}
            <TableHead>Type</TableHead>
            <TableHead>Dates</TableHead>
            <TableHead className="text-right">Days</TableHead>
            <TableHead>Reason</TableHead>
            {showStatus && <TableHead>Status</TableHead>}
            <TableHead>Requested</TableHead>
            {renderActions && <TableHead className="text-right">Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {requests.map((r) => (
            <TableRow key={r.id}>
              {showEmployee && <TableCell className="font-medium">{r.employee_name}</TableCell>}
              <TableCell>{r.leave_type.name}</TableCell>
              <TableCell className="whitespace-nowrap">{dateRange(r.start_date, r.end_date)}</TableCell>
              <TableCell className="tabular text-right">{formatDays(r.days)}</TableCell>
              <TableCell className="max-w-56 truncate text-muted-foreground" title={r.reason}>
                {r.decision_comment && r.status === "REJECTED"
                  ? `Rejected: ${r.decision_comment}`
                  : r.reason || "—"}
              </TableCell>
              {showStatus && (
                <TableCell>
                  <StatusBadge status={r.status} />
                </TableCell>
              )}
              <TableCell className="whitespace-nowrap text-muted-foreground">
                {formatDate(r.created_at)}
              </TableCell>
              {renderActions && <TableCell className="text-right">{renderActions(r)}</TableCell>}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
