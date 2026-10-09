"use server";

import { refresh } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api/client";
import type {
  ActionResult,
  CreateEmployeeInput,
  EmployeeDetail,
  UpdateEmployeeInput,
} from "@/lib/api/types";

// Like every Server Action, these only forward the caller's session; the API decides
// whether they may manage anyone (HR_ADMIN, own company, never their own record).

async function run(
  fn: () => Promise<EmployeeDetail>,
  message: (e: EmployeeDetail) => string,
  { revalidate = true } = {},
): Promise<ActionResult<EmployeeDetail>> {
  try {
    const data = await fn();
    if (revalidate) refresh();
    return { ok: true, data, message: message(data) };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.message };
    return { ok: false, error: "Something went wrong. Please try again." };
  }
}

const path = (id: string) => `/employees/${encodeURIComponent(id)}`;

export async function createEmployeeAction(input: CreateEmployeeInput) {
  return run(
    () => apiFetch<EmployeeDetail>("/employees", { method: "POST", body: input }),
    (e) => `${e.full_name} added as ${e.employee_code}.`,
  );
}

/** Read-only: used to prefill the edit form with fields the list view doesn't carry. */
export async function getEmployeeAction(id: string) {
  return run(() => apiFetch<EmployeeDetail>(path(id)), () => "", { revalidate: false });
}

export async function updateEmployeeAction(id: string, input: UpdateEmployeeInput) {
  return run(
    () => apiFetch<EmployeeDetail>(path(id), { method: "PATCH", body: input }),
    (e) => `${e.full_name}'s record was updated.`,
  );
}

export async function resetPasswordAction(id: string, newPassword: string): Promise<ActionResult> {
  try {
    await apiFetch<undefined>(`${path(id)}/reset-password`, {
      method: "POST",
      body: { new_password: newPassword },
    });
    return { ok: true, message: "Password reset. They have been signed out everywhere." };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.message };
    return { ok: false, error: "Something went wrong. Please try again." };
  }
}

export async function setEmployeeActiveAction(id: string, active: boolean) {
  return run(
    () =>
      apiFetch<EmployeeDetail>(`${path(id)}/${active ? "reactivate" : "deactivate"}`, {
        method: "POST",
      }),
    (e) => (active ? `${e.full_name} has been reactivated.` : `${e.full_name} has been deactivated.`),
  );
}
