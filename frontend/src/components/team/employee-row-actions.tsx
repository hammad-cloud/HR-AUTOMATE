"use client";

import { useEffect, useState, useTransition } from "react";
import {
  CheckCircle2,
  ChevronDown,
  KeyRound,
  Loader2,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  UserCheck,
  UserX,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getEmployeeAction,
  resetPasswordAction,
  setEmployeeActiveAction,
  updateEmployeeAction,
} from "@/lib/actions/employees";
import type {
  AssignableRole,
  EmployeeDetail,
  EmployeeSummary,
  UpdateEmployeeInput,
} from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/navigation";
import { generatePassword } from "@/lib/password";

const NO_MANAGER = "none";
const ROLES: AssignableRole[] = ["EMPLOYEE", "MANAGER", "HR_ADMIN"];

/** Per-row HR actions on the People page. Hidden on the admin's own row: the API refuses it. */
export function EmployeeRowActions({
  employee,
  employees,
  trigger = "icon",
}: {
  employee: EmployeeSummary;
  employees: EmployeeSummary[];
  /** "icon" for table rows, "button" for the profile page header. */
  trigger?: "icon" | "button";
}) {
  const [editOpen, setEditOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          {trigger === "icon" ? (
            <Button size="icon" variant="ghost" aria-label={`Manage ${employee.full_name}`}>
              <MoreHorizontal aria-hidden />
            </Button>
          ) : (
            <Button variant="outline">
              Manage <ChevronDown aria-hidden />
            </Button>
          )}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {employee.is_active ? (
            <>
              <DropdownMenuItem onSelect={() => setEditOpen(true)}>
                <Pencil aria-hidden /> Edit details
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setResetOpen(true)}>
                <KeyRound aria-hidden /> Reset password
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onSelect={() => setStatusOpen(true)}>
                <UserX aria-hidden /> Deactivate
              </DropdownMenuItem>
            </>
          ) : (
            <DropdownMenuItem onSelect={() => setStatusOpen(true)}>
              <UserCheck aria-hidden /> Reactivate
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {editOpen && (
        <EditEmployeeDialog
          employeeId={employee.id}
          employees={employees}
          onClose={() => setEditOpen(false)}
        />
      )}
      <StatusDialog employee={employee} open={statusOpen} onOpenChange={setStatusOpen} />
      {resetOpen && (
        <ResetPasswordDialog employee={employee} onClose={() => setResetOpen(false)} />
      )}
    </>
  );
}

function ResetPasswordDialog({
  employee,
  onClose,
}: {
  employee: EmployeeSummary;
  onClose: () => void;
}) {
  const [password, setPassword] = useState(generatePassword);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [pending, startTransition] = useTransition();

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await resetPasswordAction(employee.id, password);
      if (result.ok) {
        toast.success(result.message);
        setDone(true);
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-md">
        {done ? (
          <div className="space-y-5">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle2 className="size-5 text-emerald-600" aria-hidden />
                Password reset
              </DialogTitle>
              <DialogDescription>
                Share this temporary password with {employee.full_name} privately. It is not shown
                again. They can change it from My Profile after signing in.
              </DialogDescription>
            </DialogHeader>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-lg bg-muted px-4 py-3 text-sm">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-medium break-all">{employee.email}</dd>
              <dt className="text-muted-foreground">Temporary password</dt>
              <dd className="font-mono font-medium break-all">{password}</dd>
            </dl>
            <DialogFooter>
              <Button onClick={onClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <DialogHeader>
              <DialogTitle>Reset password for {employee.full_name}?</DialogTitle>
              <DialogDescription>
                Their current password stops working and they are signed out on every device.
              </DialogDescription>
            </DialogHeader>
            {error && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="reset-password">Temporary password</Label>
              <div className="flex gap-2">
                <Input
                  id="reset-password"
                  className="font-mono"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  maxLength={128}
                  autoComplete="new-password"
                  required
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => setPassword(generatePassword())}
                  aria-label="Generate a new password"
                >
                  <RefreshCw aria-hidden />
                </Button>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={pending || password.length < 8}>
                {pending && <Loader2 className="animate-spin" aria-hidden />}
                Reset password
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function StatusDialog({
  employee,
  open,
  onOpenChange,
}: {
  employee: EmployeeSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const deactivating = employee.is_active;

  function confirm() {
    setError(null);
    startTransition(async () => {
      const result = await setEmployeeActiveAction(employee.id, !deactivating);
      if (result.ok) {
        toast.success(result.message);
        onOpenChange(false);
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setError(null);
        onOpenChange(next);
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {deactivating ? `Deactivate ${employee.full_name}?` : `Reactivate ${employee.full_name}?`}
          </DialogTitle>
          <DialogDescription>
            {deactivating
              ? "They are signed out and can no longer sign in. Their pending leave requests are cancelled. Their records stay, and you can reactivate them later."
              : "They can sign in again with their existing password. If their previous manager has left, assign a new one afterwards."}
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Keep as is
          </Button>
          <Button
            variant={deactivating ? "destructive" : "default"}
            disabled={pending}
            onClick={confirm}
          >
            {pending && <Loader2 className="animate-spin" aria-hidden />}
            {deactivating ? "Deactivate" : "Reactivate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface FormState {
  fullName: string;
  department: string;
  jobTitle: string;
  managerId: string;
  salary: string;
  role: AssignableRole;
}

function toForm(e: EmployeeDetail): FormState {
  return {
    fullName: e.full_name,
    department: e.department,
    jobTitle: e.job_title,
    managerId: e.manager_id ?? NO_MANAGER,
    salary: e.salary ?? "",
    role: e.role === "PLATFORM_ADMIN" || !e.role ? "EMPLOYEE" : e.role,
  };
}

/** Only the fields that actually changed, so the audit log records the real edit. */
function diff(before: FormState, after: FormState): UpdateEmployeeInput {
  const changes: UpdateEmployeeInput = {};
  if (after.fullName.trim() !== before.fullName) changes.full_name = after.fullName.trim();
  if (after.department.trim() !== before.department) changes.department = after.department.trim();
  if (after.jobTitle.trim() !== before.jobTitle) changes.job_title = after.jobTitle.trim();
  if (after.managerId !== before.managerId)
    changes.manager_id = after.managerId === NO_MANAGER ? null : after.managerId;
  if (Number(after.salary) !== Number(before.salary)) changes.salary = after.salary;
  if (after.role !== before.role) changes.role = after.role;
  return changes;
}

function EditEmployeeDialog({
  employeeId,
  employees,
  onClose,
}: {
  employeeId: string;
  employees: EmployeeSummary[];
  onClose: () => void;
}) {
  const [original, setOriginal] = useState<FormState | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, startSaving] = useTransition();

  // The list row lacks salary, manager and role, so fetch the full record on open.
  useEffect(() => {
    let cancelled = false;
    getEmployeeAction(employeeId).then((result) => {
      if (cancelled) return;
      if (result.ok && result.data) {
        setOriginal(toForm(result.data));
        setForm(toForm(result.data));
        setName(result.data.full_name);
      } else {
        setError(result.ok ? "Could not load this employee." : result.error);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [employeeId]);

  const departments = [...new Set(employees.map((e) => e.department))].sort();
  const managers = employees.filter((e) => e.id !== employeeId && e.is_active);
  const changes = original && form ? diff(original, form) : {};
  const dirty = Object.keys(changes).length > 0;
  const set = (field: keyof FormState) => (value: string) =>
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!dirty) return;
    setError(null);
    startSaving(async () => {
      const result = await updateEmployeeAction(employeeId, changes);
      if (result.ok) {
        toast.success(result.message);
        onClose();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <form onSubmit={submit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>{name ? `Edit ${name}` : "Edit employee"}</DialogTitle>
            <DialogDescription>
              Email, CNIC and joining date can&apos;t be changed. A role change signs them out so
              their new access applies straight away.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!form ? (
            !error && (
              <div className="grid gap-4 sm:grid-cols-2" aria-busy>
                {Array.from({ length: 6 }, (_, i) => (
                  <Skeleton key={i} className="h-14" />
                ))}
              </div>
            )
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="edit-name">Full name</Label>
                <Input
                  id="edit-name"
                  value={form.fullName}
                  onChange={(e) => set("fullName")(e.target.value)}
                  maxLength={160}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-department">Department</Label>
                <Input
                  id="edit-department"
                  list="edit-department-options"
                  value={form.department}
                  onChange={(e) => set("department")(e.target.value)}
                  maxLength={80}
                  required
                />
                <datalist id="edit-department-options">
                  {departments.map((d) => (
                    <option key={d} value={d} />
                  ))}
                </datalist>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-title">Job title</Label>
                <Input
                  id="edit-title"
                  value={form.jobTitle}
                  onChange={(e) => set("jobTitle")(e.target.value)}
                  maxLength={120}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-manager">Reports to</Label>
                <Select value={form.managerId} onValueChange={set("managerId")}>
                  <SelectTrigger id="edit-manager" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NO_MANAGER}>No manager</SelectItem>
                    {managers.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        {e.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-role">Access role</Label>
                <Select value={form.role} onValueChange={set("role")}>
                  <SelectTrigger id="edit-role" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((r) => (
                      <SelectItem key={r} value={r}>
                        {ROLE_LABELS[r]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="edit-salary">Monthly salary (PKR)</Label>
                <Input
                  id="edit-salary"
                  type="number"
                  inputMode="decimal"
                  min={1}
                  step="0.01"
                  value={form.salary}
                  onChange={(e) => set("salary")(e.target.value)}
                  required
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !dirty}>
              {saving && <Loader2 className="animate-spin" aria-hidden />}
              Save changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
