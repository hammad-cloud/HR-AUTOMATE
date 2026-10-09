// Mirrors the FastAPI response schemas (backend/app/schemas). Decimals arrive as strings.

export type Role = "EMPLOYEE" | "MANAGER" | "HR_ADMIN" | "PLATFORM_ADMIN";

export interface CurrentUser {
  user_id: string;
  email: string;
  role: Role;
  tenant_id: string | null;
  tenant_name: string | null;
  company_id: string | null;
  employee_id: string | null;
  full_name: string;
  job_title: string | null;
  department: string | null;
}

export interface EmployeeSummary {
  id: string;
  employee_code: string;
  full_name: string;
  email: string;
  department: string;
  job_title: string;
  is_active: boolean;
}

export interface EmployeeDetail extends EmployeeSummary {
  manager_id: string | null;
  manager_name: string | null;
  join_date: string;
  role: Role | null;
  salary: string | null;
  salary_masked: boolean;
}

/** Roles HR can assign when onboarding; PLATFORM_ADMIN is never assignable. */
export type AssignableRole = Exclude<Role, "PLATFORM_ADMIN">;

export interface CreateEmployeeInput {
  full_name: string;
  email: string;
  department: string;
  job_title: string;
  manager_id: string | null;
  join_date: string;
  salary: string;
  national_id: string;
  role: AssignableRole;
  password: string;
}

/** Partial update: send only changed fields. `manager_id: null` removes the manager. */
export type UpdateEmployeeInput = Partial<
  Pick<CreateEmployeeInput, "full_name" | "department" | "job_title" | "manager_id" | "salary" | "role">
>;

export interface LeaveType {
  id: string;
  code: string;
  name: string;
  annual_quota: number;
}

export interface LeaveBalance {
  leave_type: LeaveType;
  year: number;
  allocated: string;
  used: string;
  pending: string;
  remaining: string;
}

export type LeaveStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface LeaveRequest {
  id: string;
  employee_id: string;
  employee_name: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days: string;
  reason: string;
  status: LeaveStatus;
  approver_id: string | null;
  decided_at: string | null;
  decision_comment: string | null;
  created_at: string;
}

export type AttendanceStatus = "PRESENT" | "LATE" | "ABSENT" | "ON_LEAVE" | "WFH";

export interface AttendanceRecord {
  date: string;
  check_in: string | null;
  check_out: string | null;
  status: AttendanceStatus;
}

export interface AttendanceReport {
  employee: EmployeeSummary;
  month: string;
  records: AttendanceRecord[];
  summary: Partial<Record<AttendanceStatus, number>>;
}

export interface Payslip {
  id: string;
  employee_id: string;
  month: string;
  gross: string;
  deductions: string;
  net: string;
}

export interface DashboardStats {
  leave_balances: LeaveBalance[];
  pending_my_requests: number;
  pending_my_approvals: number;
  attendance_this_month: Partial<Record<AttendanceStatus, number>>;
  team_size: number | null;
  headcount: number | null;
}

export interface AuditEntry {
  id: number;
  ts: string;
  tenant_id: string | null;
  user_id: string | null;
  channel: string;
  event: string;
  tool: string | null;
  outcome: string;
  approval_status: string | null;
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  cost_usd: string | null;
  // Absent for PLATFORM_ADMIN (metadata-only view).
  conversation_id?: string | null;
  request_id?: string | null;
  user_message?: string | null;
  args_redacted?: Record<string, unknown> | null;
  detail?: string | null;
  actor_name?: string | null;
  subject_name?: string | null;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; request_id: string | null };
}

/** Result shape returned by Server Actions to client components. */
export type ActionResult<T = undefined> =
  | { ok: true; data?: T; message?: string }
  | { ok: false; error: string };
