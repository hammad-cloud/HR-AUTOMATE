import type { Role } from "@/lib/api/types";

/**
 * Stable route registry (FR-04). The same list feeds the sidebar and, later, the assistant's
 * `navigate_to` tool allow-list, so the copilot can only deep-link to screens the role may open.
 */
export interface AppRoute {
  href: string;
  label: string;
  description: string;
  icon:
    | "dashboard"
    | "profile"
    | "leave"
    | "approvals"
    | "attendance"
    | "payslips"
    | "team"
    | "audit";
  roles: Role[];
  section: "Workspace" | "Manage" | "Admin";
}

const HR_ROLES: Role[] = ["EMPLOYEE", "MANAGER", "HR_ADMIN"];

export const APP_ROUTES: AppRoute[] = [
  { href: "/dashboard", label: "Dashboard", description: "Your HR overview", icon: "dashboard",
    roles: [...HR_ROLES, "PLATFORM_ADMIN"], section: "Workspace" },
  { href: "/profile", label: "My Profile", description: "Personal and job details", icon: "profile",
    roles: HR_ROLES, section: "Workspace" },
  { href: "/leave", label: "Leave", description: "Balances, requests and applications",
    icon: "leave", roles: HR_ROLES, section: "Workspace" },
  { href: "/attendance", label: "Attendance", description: "Monthly attendance record",
    icon: "attendance", roles: HR_ROLES, section: "Workspace" },
  { href: "/payslips", label: "Payslips", description: "Monthly salary statements",
    icon: "payslips", roles: HR_ROLES, section: "Workspace" },
  { href: "/leave/approvals", label: "Approvals", description: "Leave requests awaiting you",
    icon: "approvals", roles: ["MANAGER", "HR_ADMIN"], section: "Manage" },
  { href: "/team", label: "Team", description: "People you manage or administer", icon: "team",
    roles: ["MANAGER", "HR_ADMIN"], section: "Manage" },
  { href: "/admin/audit", label: "Audit Log", description: "Every action and denial, recorded",
    icon: "audit", roles: ["HR_ADMIN", "PLATFORM_ADMIN"], section: "Admin" },
];

export function routesFor(role: Role): AppRoute[] {
  return APP_ROUTES.filter((route) => route.roles.includes(role)).map((route) =>
    // HR administers the whole company; "Team" only fits a manager's view.
    route.href === "/team" && role === "HR_ADMIN"
      ? { ...route, label: "People", description: "Everyone in your company" }
      : route,
  );
}

export const ROLE_LABELS: Record<Role, string> = {
  EMPLOYEE: "Employee",
  MANAGER: "Manager",
  HR_ADMIN: "HR Admin",
  PLATFORM_ADMIN: "Platform Admin",
};
