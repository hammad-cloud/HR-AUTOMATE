"use server";

import { refresh } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api/client";
import type { ActionResult, LeaveRequest } from "@/lib/api/types";

// Server Actions are public POST endpoints. They hold no authority of their own: each one
// forwards the caller's session token, and the API re-authorizes every request.

async function run(
  fn: () => Promise<LeaveRequest>,
  successMessage: string,
): Promise<ActionResult<LeaveRequest>> {
  try {
    const data = await fn();
    refresh();
    return { ok: true, data, message: successMessage };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.message };
    return { ok: false, error: "Something went wrong. Please try again." };
  }
}

export interface ApplyLeaveInput {
  leaveTypeCode: string;
  startDate: string;
  endDate: string;
  reason: string;
  /** Generated once per form submission so double-clicks never create duplicates (FR-42). */
  idempotencyKey: string;
}

export async function applyLeaveAction(input: ApplyLeaveInput) {
  return run(
    () =>
      apiFetch<LeaveRequest>("/leave/requests", {
        method: "POST",
        headers: { "Idempotency-Key": input.idempotencyKey },
        body: {
          leave_type_code: input.leaveTypeCode,
          start_date: input.startDate,
          end_date: input.endDate,
          reason: input.reason,
        },
      }),
    "Leave request submitted for approval.",
  );
}

export async function decideLeaveAction(
  requestId: string,
  decision: "approve" | "reject",
  comment?: string,
) {
  return run(
    () =>
      apiFetch<LeaveRequest>(`/leave/requests/${encodeURIComponent(requestId)}/${decision}`, {
        method: "POST",
        body: { comment: comment || null },
      }),
    decision === "approve" ? "Leave approved." : "Leave rejected.",
  );
}

export async function cancelLeaveAction(requestId: string) {
  return run(
    () =>
      apiFetch<LeaveRequest>(`/leave/requests/${encodeURIComponent(requestId)}/cancel`, {
        method: "POST",
      }),
    "Leave request cancelled.",
  );
}
