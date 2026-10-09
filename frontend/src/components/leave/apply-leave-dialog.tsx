"use client";

import { useMemo, useState, useTransition } from "react";
import { Loader2, Plus } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { applyLeaveAction } from "@/lib/actions/leave";
import type { LeaveBalance } from "@/lib/api/types";

function countWeekdays(start: string, end: string): number {
  if (!start || !end || end < start) return 0;
  let days = 0;
  for (let d = new Date(`${start}T00:00:00`); d <= new Date(`${end}T00:00:00`); ) {
    if (d.getDay() % 6 !== 0) days += 1;
    d.setDate(d.getDate() + 1);
  }
  return days;
}

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function ApplyLeaveDialog({
  balances,
  defaultOpen = false,
}: {
  balances: LeaveBalance[];
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [type, setType] = useState(balances[0]?.leave_type.code ?? "");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  // One key per dialog session: retries and double-clicks reuse it, so the server
  // creates at most one request (FR-42).
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [pending, startTransition] = useTransition();

  const days = useMemo(() => countWeekdays(start, end), [start, end]);
  const balance = balances.find((b) => b.leave_type.code === type);
  const available = balance ? Number(balance.remaining) - Number(balance.pending) : 0;

  function reset() {
    setStart("");
    setEnd("");
    setReason("");
    setError(null);
    setIdempotencyKey(crypto.randomUUID());
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await applyLeaveAction({
        leaveTypeCode: type,
        startDate: start,
        endDate: end,
        reason,
        idempotencyKey,
      });
      if (result.ok) {
        toast.success(result.message);
        setOpen(false);
        reset();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden /> Apply for leave
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>Apply for leave</DialogTitle>
            <DialogDescription>
              Your request goes to your manager for approval. Weekends are not counted.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="leave-type">Leave type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger id="leave-type" className="w-full">
                <SelectValue placeholder="Select a leave type" />
              </SelectTrigger>
              <SelectContent>
                {balances.map((b) => (
                  <SelectItem key={b.leave_type.code} value={b.leave_type.code}>
                    {b.leave_type.name} ({Number(b.remaining) - Number(b.pending)} available)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="start">From</Label>
              <Input
                id="start"
                type="date"
                min={todayIso()}
                value={start}
                onChange={(e) => {
                  setStart(e.target.value);
                  if (!end || end < e.target.value) setEnd(e.target.value);
                }}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end">To</Label>
              <Input
                id="end"
                type="date"
                min={start || todayIso()}
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="reason">Reason</Label>
            <Textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
              placeholder="Optional, e.g. family event"
              rows={3}
            />
          </div>

          <p className="rounded-lg bg-muted px-3 py-2 text-sm" aria-live="polite">
            {days > 0 ? (
              <>
                <span className="font-medium">{days} working day{days === 1 ? "" : "s"}</span>
                {days > available && (
                  <span className="text-destructive"> · exceeds your {available} available</span>
                )}
              </>
            ) : (
              <span className="text-muted-foreground">Select dates to see the day count.</span>
            )}
          </p>

          <DialogFooter>
            <Button type="submit" disabled={pending || !type || !start || !end}>
              {pending && <Loader2 className="animate-spin" aria-hidden />}
              Submit request
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
