"use client";

import { useActionState, useState } from "react";
import { Loader2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginAction, type LoginState } from "@/lib/actions/auth";
import { PERSONAS } from "@/lib/demo-personas";
import { cn } from "@/lib/utils";

const ROLE_TONE: Record<string, string> = {
  "HR Admin": "bg-primary/10 text-primary",
  Manager: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  Employee: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  "Super Admin": "bg-amber-500/10 text-amber-700 dark:text-amber-300",
};

function initialsOf(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function LoginForm() {
  const [state, formAction, pending] = useActionState<LoginState, FormData>(loginAction, {});
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-8">
      <form
        id="login-form"
        action={formAction}
        className="space-y-5 rounded-xl border bg-card p-6 shadow-sm"
      >
        {state.error && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{state.error}</AlertDescription>
          </Alert>
        )}
        <div className="space-y-2">
          <Label htmlFor="email">Work email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            defaultValue={state.email}
            placeholder="you@company.com"
            className="h-10"
            onChange={() => setSelected(null)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            className="h-10"
            required
          />
        </div>
        <Button type="submit" size="lg" className="h-10 w-full" disabled={pending}>
          {pending && <Loader2 className="animate-spin" aria-hidden />}
          {pending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="h-px flex-1 bg-border" />
          <p className="text-xs font-medium text-muted-foreground">
            Demo personas · one-click sign in
          </p>
          <span className="h-px flex-1 bg-border" />
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {PERSONAS.map((p) => (
            <button
              key={p.email}
              type="submit"
              form="login-form"
              name="demo"
              value={p.email}
              formNoValidate
              disabled={pending}
              onClick={() => setSelected(p.email)}
              aria-pressed={selected === p.email}
              className={cn(
                "flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/40 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-ring",
                selected === p.email && "border-primary ring-1 ring-primary",
              )}
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                {initialsOf(p.name)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{p.name}</span>
                <span className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-1.5 py-px text-[11px] font-medium",
                      ROLE_TONE[p.role],
                    )}
                  >
                    {p.role}
                  </span>
                  <span className="truncate">{p.tenant}</span>
                </span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
