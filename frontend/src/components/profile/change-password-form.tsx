"use client";

import { useState, useTransition } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { changePasswordAction } from "@/lib/actions/auth";

const MIN_LENGTH = 8;

export function ChangePasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const mismatch = confirm.length > 0 && confirm !== next;
  const sameAsCurrent = next.length > 0 && next === current;
  const canSubmit =
    current.length > 0 && next.length >= MIN_LENGTH && next === confirm && !sameAsCurrent;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await changePasswordAction({ currentPassword: current, newPassword: next });
      if (result.ok) {
        toast.success(result.message);
        setCurrent("");
        setNext("");
        setConfirm("");
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <form onSubmit={submit} className="max-w-2xl space-y-4">
      {error && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="space-y-2">
        <Label htmlFor="current-password">Current password</Label>
        <Input
          id="current-password"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          maxLength={128}
          required
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="new-password">New password</Label>
          <Input
            id="new-password"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            minLength={MIN_LENGTH}
            maxLength={128}
            aria-describedby="new-password-hint"
            required
          />
          <p id="new-password-hint" className="text-xs text-muted-foreground" aria-live="polite">
            {sameAsCurrent ? (
              <span className="text-destructive">Choose a password you haven&apos;t just used.</span>
            ) : (
              `At least ${MIN_LENGTH} characters.`
            )}
          </p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm-password">Confirm new password</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            maxLength={128}
            aria-invalid={mismatch}
            aria-describedby="confirm-password-hint"
            required
          />
          <p id="confirm-password-hint" className="text-xs text-destructive" aria-live="polite">
            {mismatch ? "Passwords don't match." : ""}
          </p>
        </div>
      </div>
      <Button type="submit" disabled={pending || !canSubmit}>
        {pending && <Loader2 className="animate-spin" aria-hidden />}
        Change password
      </Button>
    </form>
  );
}
