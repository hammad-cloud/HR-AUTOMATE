"use client";

import { useState, useTransition } from "react";
import { CheckCircle2, Loader2, RefreshCw, UserPlus } from "lucide-react";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createEmployeeAction } from "@/lib/actions/employees";
import type { AssignableRole, EmployeeDetail, EmployeeSummary } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/navigation";
import { generatePassword } from "@/lib/password";

const NO_MANAGER = "none";
const ROLES: AssignableRole[] = ["EMPLOYEE", "MANAGER", "HR_ADMIN"];

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

const EMPTY = {
  fullName: "",
  email: "",
  department: "",
  jobTitle: "",
  managerId: NO_MANAGER,
  joinDate: "",
  salary: "",
  nationalId: "",
  role: "EMPLOYEE" as AssignableRole,
};

export function AddEmployeeDialog({ employees }: { employees: EmployeeSummary[] }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<EmployeeDetail | null>(null);
  const [pending, startTransition] = useTransition();

  const departments = [...new Set(employees.map((e) => e.department))].sort();
  const set = (field: keyof typeof EMPTY) => (value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  function reset() {
    setForm({ ...EMPTY, joinDate: todayIso() });
    setPassword(generatePassword());
    setError(null);
    setCreated(null);
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await createEmployeeAction({
        full_name: form.fullName,
        email: form.email,
        department: form.department,
        job_title: form.jobTitle,
        manager_id: form.managerId === NO_MANAGER ? null : form.managerId,
        join_date: form.joinDate,
        salary: form.salary,
        national_id: form.nationalId,
        role: form.role,
        password,
      });
      if (result.ok) {
        toast.success(result.message);
        setCreated(result.data ?? null);
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) reset();
        setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <UserPlus aria-hidden /> Add employee
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        {created ? (
          <div className="space-y-5">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle2 className="size-5 text-emerald-600" aria-hidden />
                {created.full_name} has been added
              </DialogTitle>
              <DialogDescription>
                Share these sign-in details with them privately. The password is not shown again.
              </DialogDescription>
            </DialogHeader>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 rounded-lg bg-muted px-4 py-3 text-sm">
              <dt className="text-muted-foreground">Employee ID</dt>
              <dd className="tabular font-medium">{created.employee_code}</dd>
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-medium break-all">{created.email}</dd>
              <dt className="text-muted-foreground">Initial password</dt>
              <dd className="font-mono font-medium break-all">{password}</dd>
            </dl>
            <DialogFooter>
              <Button variant="outline" onClick={reset}>
                Add another
              </Button>
              <Button onClick={() => setOpen(false)}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <DialogHeader>
              <DialogTitle>Add employee</DialogTitle>
              <DialogDescription>
                Creates their HR record, a login account and this year&apos;s leave balances
                (pro-rated from the joining date).
              </DialogDescription>
            </DialogHeader>

            {error && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="full-name">Full name</Label>
                <Input
                  id="full-name"
                  value={form.fullName}
                  onChange={(e) => set("fullName")(e.target.value)}
                  maxLength={160}
                  required
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="email">Work email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => set("email")(e.target.value)}
                  maxLength={254}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="department">Department</Label>
                <Input
                  id="department"
                  list="department-options"
                  value={form.department}
                  onChange={(e) => set("department")(e.target.value)}
                  maxLength={80}
                  required
                />
                <datalist id="department-options">
                  {departments.map((d) => (
                    <option key={d} value={d} />
                  ))}
                </datalist>
              </div>
              <div className="space-y-2">
                <Label htmlFor="job-title">Job title</Label>
                <Input
                  id="job-title"
                  value={form.jobTitle}
                  onChange={(e) => set("jobTitle")(e.target.value)}
                  maxLength={120}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="manager">Reports to</Label>
                <Select value={form.managerId} onValueChange={set("managerId")}>
                  <SelectTrigger id="manager" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NO_MANAGER}>No manager</SelectItem>
                    {employees.map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        {e.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Access role</Label>
                <Select value={form.role} onValueChange={set("role")}>
                  <SelectTrigger id="role" className="w-full">
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
              <div className="space-y-2">
                <Label htmlFor="join-date">Joining date</Label>
                <Input
                  id="join-date"
                  type="date"
                  value={form.joinDate}
                  onChange={(e) => set("joinDate")(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="salary">Monthly salary (PKR)</Label>
                <Input
                  id="salary"
                  type="number"
                  inputMode="decimal"
                  min={1}
                  step="0.01"
                  value={form.salary}
                  onChange={(e) => set("salary")(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="national-id">CNIC</Label>
                <Input
                  id="national-id"
                  value={form.nationalId}
                  onChange={(e) => set("nationalId")(e.target.value)}
                  pattern="\d{5}-\d{7}-\d"
                  title="Format: 12345-1234567-1"
                  placeholder="12345-1234567-1"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Initial password</Label>
                <div className="flex gap-2">
                  <Input
                    id="password"
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
            </div>

            <DialogFooter>
              <Button type="submit" disabled={pending}>
                {pending && <Loader2 className="animate-spin" aria-hidden />}
                Add employee
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
