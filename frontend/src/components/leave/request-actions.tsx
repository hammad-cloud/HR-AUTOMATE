"use client";

import { useState, useTransition } from "react";
import { Check, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cancelLeaveAction, decideLeaveAction } from "@/lib/actions/leave";
import type { ActionResult, LeaveRequest } from "@/lib/api/types";

function useAction() {
  const [pending, startTransition] = useTransition();
  function run(fn: () => Promise<ActionResult<LeaveRequest>>, onDone?: () => void) {
    startTransition(async () => {
      const result = await fn();
      if (result.ok) {
        toast.success(result.message);
        onDone?.();
      } else {
        toast.error(result.error);
      }
    });
  }
  return { pending, run };
}

export function ApprovalActions({ request }: { request: LeaveRequest }) {
  const { pending, run } = useAction();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");

  return (
    <div className="flex justify-end gap-2">
      <Button
        size="sm"
        disabled={pending}
        onClick={() => run(() => decideLeaveAction(request.id, "approve"))}
        aria-label={`Approve leave for ${request.employee_name}`}
      >
        {pending ? <Loader2 className="animate-spin" aria-hidden /> : <Check aria-hidden />}
        Approve
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={pending}
        onClick={() => setRejectOpen(true)}
        aria-label={`Reject leave for ${request.employee_name}`}
      >
        <X aria-hidden /> Reject
      </Button>

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject leave request</DialogTitle>
            <DialogDescription>
              {request.employee_name} will see this reason. A reason is required.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor={`reject-${request.id}`}>Reason</Label>
            <Textarea
              id={`reject-${request.id}`}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button
              variant="destructive"
              disabled={pending || !reason.trim()}
              onClick={() =>
                run(
                  () => decideLeaveAction(request.id, "reject", reason.trim()),
                  () => setRejectOpen(false),
                )
              }
            >
              {pending && <Loader2 className="animate-spin" aria-hidden />}
              Reject request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function CancelRequestButton({ requestId }: { requestId: string }) {
  const { pending, run } = useAction();
  return (
    <Button
      size="sm"
      variant="ghost"
      disabled={pending}
      onClick={() => run(() => cancelLeaveAction(requestId))}
    >
      {pending && <Loader2 className="animate-spin" aria-hidden />}
      Cancel
    </Button>
  );
}
