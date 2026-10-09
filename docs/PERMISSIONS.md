# Permission model

Access is evaluated on four levels for every read, retrieval and action:
**Tenant → Company → Role → User (ownership / reporting line).**

## Role-permission matrix (BRD §4.1)

Encoded in `backend/app/permissions/policy.py` (`MATRIX`) and covered by
`backend/tests/unit/test_policy.py`.

| Capability | EMPLOYEE | MANAGER | HR_ADMIN | PLATFORM_ADMIN |
|---|---|---|---|---|
| Ask product / policy questions | Yes | Yes | Yes | Yes |
| View employee profile | Own | Team + own | Company | No |
| Add / edit / deactivate employee, reset their password | No | No | Company (not own) | No |
| Change own password | Yes | Yes | Yes | Yes |
| View leave balance | Own | Team + own | Company | No |
| Apply for leave | Own | Own | Own | No |
| Approve / reject leave | No | Team (not own) | Company (not own) | No |
| Cancel leave | Own (pending only) | Own | Company | No |
| View attendance | Own | Team + own | Company | No |
| View payslip / salary | Own | Own | Company | No |
| Company analytics | No | Team only | Company | No |
| View audit log | No | No | Company | All tenants (metadata only) |

"Team" means direct reports (`employees.manager_id = caller.employee_id`).

Onboarding (`POST /api/v1/employees`) creates the employee, their login and pro-rated leave
balances in one transaction. HR can assign EMPLOYEE, MANAGER or HR_ADMIN, never PLATFORM_ADMIN;
the chosen manager must pass the same `resolve_target()` check as any other record lookup.

Editing and deactivation (`PATCH /employees/{id}`, `POST /employees/{id}/deactivate|reactivate`)
are self-excluded like leave approval: an HR admin can't raise their own salary, change their own
role or deactivate themselves. Reporting loops are rejected, and a manager with active reports
can't be deactivated until they are reassigned. The database grants for this are column-level
(migration 0004), so email, CNIC and employee code are immutable even to the API role.

**Sessions follow the account.** Every authenticated request re-reads the caller's `users` row
(`ensure_session_current`). A deactivated account or a changed role invalidates the existing JWT
immediately instead of at expiry. A password change or HR reset sets `users.password_changed_at`,
and any token whose `iat` (issued with sub-second precision) is older is rejected. Changing your
own password returns a fresh token for the current device; an HR reset signs the employee out
everywhere.

The employee profile page (`/team/{id}`) reuses the same endpoints, so it shows exactly what the
policy allows: managers see their reports with salary masked and no payslips; HR sees everything
and gets the management actions (except on their own record).

## Enforcement rules

| Rule | Implementation |
|---|---|
| PR-1 RLS on every tenant table | `0002_row_level_security.py`; context set per transaction from the JWT |
| PR-2 Caller's identity, no service account | Every service takes `RequestContext`; the API role has no bypass |
| PR-3 IDs re-validated server-side | `resolve_target()` loads through RLS, then `authorize()` |
| PR-4 Retrieval filtered by tenant + visibility | `visibility_filter` policy on `documents` / `doc_chunks` |
| PR-5 Salary masked | `can_view_salary()` applied in `get_employee()` |
| PR-6 No self-approval | `_SELF_EXCLUDED` in the policy engine |
| PR-7 Typed `PERMISSION_DENIED`, audited | `PermissionDeniedError` + central handler in `app/main.py` |

## Database policies

| Table(s) | Policy |
|---|---|
| companies, employees, leave_*, attendance, payslips | `tenant_id = app_current_tenant()` (read and write) |
| tenants | `id = app_current_tenant()` |
| users | own tenant, or own row (platform admin) |
| documents, doc_chunks | global or own tenant, and `role:HR_ADMIN` docs only for HR admins |
| conversations, action_proposals | owner only |
| messages | belongs to a visible conversation |
| audit_log | read: own tenant (platform admin: all); insert: must match caller; **no update/delete grant** |

With no context set, the helper functions return `NULL` and every policy is false: the
database **fails closed**.

## Why "not found" and "forbidden" look the same

When a caller references a record in another tenant, RLS hides it. The API answers with the same
`PERMISSION_DENIED` it uses for in-tenant scope violations, so IDs can't be probed to learn
whether they exist.
