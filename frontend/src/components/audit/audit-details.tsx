"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { StatusBadge } from "@/components/shared/status-badge";
import type { AuditEntry } from "@/lib/api/types";
import {
  OUTCOME_LABELS,
  actionLabel,
  detailRows,
  isDenied,
  reasonText,
  sourceLabel,
} from "@/lib/audit-format";
import { formatDate } from "@/lib/format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-3 py-2.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

export function AuditDetails({ entry }: { entry: AuditEntry }) {
  const action = actionLabel(entry);
  const rows = detailRows(entry);
  const when = `${formatDate(entry.ts, { weekday: "short" })}, ${new Date(entry.ts).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" aria-label={`Details: ${action}`}>
          Details
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isDenied(entry) ? `Blocked: ${action}` : action}</DialogTitle>
          <DialogDescription>
            Audit records can&apos;t be edited or deleted. Salaries and ID numbers are hidden
            before storage.
          </DialogDescription>
        </DialogHeader>
        <dl className="divide-y">
          <Row label="When">{when}</Row>
          <Row label="Who">{entry.actor_name ?? "Unknown user"}</Row>
          {entry.subject_name && <Row label="Employee">{entry.subject_name}</Row>}
          <Row label="Outcome">
            <StatusBadge status={entry.outcome} label={OUTCOME_LABELS[entry.outcome]} />
          </Row>
          {entry.detail && <Row label="Reason">{reasonText(entry.detail)}</Row>}
          {rows.map((r) => (
            <Row key={r.label} label={r.label}>
              {r.value}
            </Row>
          ))}
          <Row label="Source">{sourceLabel(entry.channel)}</Row>
          {entry.request_id && (
            <Row label="Reference">
              <span className="font-mono text-xs text-muted-foreground">{entry.request_id}</span>
            </Row>
          )}
        </dl>
      </DialogContent>
    </Dialog>
  );
}
