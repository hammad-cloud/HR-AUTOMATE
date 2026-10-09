import type { AuditEntry, Role } from "@/lib/api/types";
import { dateRange, formatDate } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/navigation";

// Turns raw audit records (event codes, routes, argument maps) into the plain language an HR
// reader expects. The stored record stays exact; only its presentation changes here.

/**
 * Actions keyed by the tool that performed them; also the "Action" filter. Labels name the
 * action, not its result, so allowed and refused rows read alike and Outcome says which.
 */
export const ACTIONS: Record<string, string> = {
  apply_leave: "Apply for leave",
  approve_leave: "Approve leave",
  reject_leave: "Reject leave",
  cancel_leave: "Cancel leave",
  create_employee: "Add employee",
  update_employee: "Edit employee",
  deactivate_employee: "Deactivate employee",
  reactivate_employee: "Reactivate employee",
  reset_password: "Reset password",
  change_password: "Change own password",
};

/** Refused requests are recorded by the route they targeted. */
const ROUTES: [method: string, pattern: RegExp, label: string][] = [
  ["GET", /^\/employees$/, "View employee list"],
  ["POST", /^\/employees$/, ACTIONS.create_employee],
  ["GET", /^\/employees\/me$/, "View own profile"],
  ["GET", /^\/employees\/\{employee_id\}$/, "View employee profile"],
  ["PATCH", /^\/employees\/\{employee_id\}$/, ACTIONS.update_employee],
  ["POST", /^\/employees\/\{employee_id\}\/deactivate$/, ACTIONS.deactivate_employee],
  ["POST", /^\/employees\/\{employee_id\}\/reactivate$/, ACTIONS.reactivate_employee],
  ["POST", /^\/employees\/\{employee_id\}\/reset-password$/, ACTIONS.reset_password],
  ["GET", /^\/leave\/balances$/, "View leave balances"],
  ["GET", /^\/leave\/requests$/, "View leave requests"],
  ["POST", /^\/leave\/requests$/, ACTIONS.apply_leave],
  ["GET", /^\/leave\/approvals$/, "View pending approvals"],
  ["POST", /^\/leave\/requests\/\{request_id\}\/approve$/, ACTIONS.approve_leave],
  ["POST", /^\/leave\/requests\/\{request_id\}\/reject$/, ACTIONS.reject_leave],
  ["POST", /^\/leave\/requests\/\{request_id\}\/cancel$/, ACTIONS.cancel_leave],
  ["POST", /^\/auth\/password$/, ACTIONS.change_password],
  ["GET", /^\/attendance$/, "View attendance"],
  ["GET", /^\/payslips$/, "View payslips"],
  ["GET", /^\/dashboard$/, "View dashboard"],
  ["GET", /^\/audit$/, "View audit log"],
];

export const OUTCOME_LABELS: Record<string, string> = {
  SUCCESS: "Success",
  PERMISSION_DENIED: "Denied",
  REJECTED: "Rejected by rule",
  ERROR: "Error",
};

const SOURCES: Record<string, string> = { api: "Web app", chat: "HR assistant" };

const FIELD_LABELS: Record<string, string> = {
  leave_type_code: "Leave type",
  reason: "Reason",
  comment: "Comment",
  full_name: "Name",
  email: "Email",
  department: "Department",
  job_title: "Job title",
  role: "Access role",
  join_date: "Joining date",
  salary: "Salary",
  national_id: "CNIC",
  employee_code: "Employee ID",
  manager_id: "Manager",
  cancelled_leave_requests: "Pending leave cancelled",
  cleared_inactive_manager: "Former manager removed",
  scope: "Scope",
  status: "Status",
  month: "Month",
  search: "Search",
};

// Identifiers are resolved to names server-side; their raw values add nothing for a reader.
const HIDDEN_FIELDS = new Set(["employee_id", "request_id", "start_date", "end_date"]);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const REDACTED = "[REDACTED]";

function sentenceCase(text: string): string {
  const spaced = text.replaceAll(/[_.-]+/g, " ").trim().toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

const LEGACY_ROLE_NAMES: Record<string, string> = {
  EMPLOYEE: "Employees",
  MANAGER: "Managers",
  HR_ADMIN: "HR admins",
  PLATFORM_ADMIN: "Platform admins",
};

/**
 * Refusal reasons recorded before the plain-language messages, e.g.
 * "Your role (EMPLOYEE) cannot view_payslip." → "Employees can't view payslip."
 */
export function reasonText(detail: string | null | undefined): string | null {
  if (!detail) return null;
  const legacy = /^Your role \((\w+)\) cannot ([\w ]+)\.$/.exec(detail);
  if (!legacy) return detail;
  const who = LEGACY_ROLE_NAMES[legacy[1]] ?? "This role";
  return `${who} can't ${legacy[2].replaceAll("_", " ")}.`;
}

export function isDenied(e: AuditEntry): boolean {
  return e.outcome === "PERMISSION_DENIED";
}

export function actionLabel(e: AuditEntry): string {
  if (e.tool && ACTIONS[e.tool]) return ACTIONS[e.tool];
  const [method, rawPath = ""] = e.event.split(" ");
  const path = rawPath.replace(/^\/api\/v1/, "");
  const match = ROUTES.find(([m, pattern]) => m === method && pattern.test(path));
  if (match) return match[2];
  return sentenceCase(e.tool ?? e.event);
}

export function sourceLabel(channel: string): string {
  return SOURCES[channel] ?? sentenceCase(channel);
}

function formatValue(key: string, value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (value === REDACTED) return "Hidden for privacy";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string" && UUID.test(value)) return key === "manager_id" ? "Changed" : null;
  if (key === "leave_type_code" && typeof value === "string") return sentenceCase(value);
  if (key === "role" && typeof value === "string") return ROLE_LABELS[value as Role] ?? value;
  if (key === "join_date" && typeof value === "string") return formatDate(value);
  if (key === "salary") return "Updated (hidden)";
  return String(value);
}

/** The record's arguments as label/value rows, ids and noise removed. */
export function detailRows(e: AuditEntry): { label: string; value: string }[] {
  const args = e.args_redacted ?? {};
  const rows: { label: string; value: string }[] = [];
  const start = args.start_date;
  const end = args.end_date;
  if (typeof start === "string" && typeof end === "string") {
    rows.push({ label: "Dates", value: dateRange(start, end) });
  }
  for (const [key, raw] of Object.entries(args)) {
    if (HIDDEN_FIELDS.has(key)) continue;
    const value = formatValue(key, raw);
    if (value) rows.push({ label: FIELD_LABELS[key] ?? sentenceCase(key), value });
  }
  return rows;
}

/** One line for the table: the reason for a refusal, otherwise the gist of what changed. */
export function summary(e: AuditEntry): string {
  const reason = reasonText(e.detail);
  if (reason) return reason;
  const args = e.args_redacted ?? {};
  switch (e.tool) {
    case "apply_leave": {
      const type = formatValue("leave_type_code", args.leave_type_code);
      const dates =
        typeof args.start_date === "string" && typeof args.end_date === "string"
          ? dateRange(args.start_date, args.end_date)
          : null;
      const reason = typeof args.reason === "string" && args.reason ? `“${args.reason}”` : null;
      return [type && `${type} leave`, dates, reason].filter(Boolean).join(" · ");
    }
    case "approve_leave":
    case "reject_leave":
      return typeof args.comment === "string" && args.comment ? `“${args.comment}”` : "";
    case "create_employee":
      return [args.job_title, args.department, formatValue("role", args.role)]
        .filter(Boolean)
        .join(" · ");
    case "update_employee": {
      const changed = Object.keys(args)
        .filter((k) => !HIDDEN_FIELDS.has(k))
        .map((k) => (FIELD_LABELS[k] ?? sentenceCase(k)).toLowerCase());
      return changed.length ? `Changed ${changed.join(", ")}` : "";
    }
    case "deactivate_employee": {
      const n = Number(args.cancelled_leave_requests ?? 0);
      return n ? `${n} pending leave request${n === 1 ? "" : "s"} cancelled` : "Sign-in blocked";
    }
    case "reactivate_employee":
      return args.cleared_inactive_manager ? "Former manager had left; manager cleared" : "Sign-in restored";
    case "reset_password":
    case "change_password":
      return "Older sessions signed out";
    default:
      return detailRows(e)
        .slice(0, 2)
        .map((r) => `${r.label}: ${r.value}`)
        .join(" · ");
  }
}
