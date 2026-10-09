import type { Metadata } from "next";
import { Building2, ShieldCheck, Sparkles, Waypoints } from "lucide-react";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

const HIGHLIGHTS = [
  {
    icon: ShieldCheck,
    title: "Isolated by design",
    body: "Tenant boundaries are enforced by Postgres row-level security, not by prompts.",
  },
  {
    icon: Waypoints,
    title: "Role-aware",
    body: "Employees, managers and HR admins each see exactly what they're entitled to.",
  },
  {
    icon: Sparkles,
    title: "Copilot-ready",
    body: "Every action is audited and every write needs your explicit confirmation.",
  },
];

function Logo({ className }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 font-semibold ${className ?? ""}`}>
      <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Building2 className="size-5" aria-hidden />
      </span>
      <span className="text-lg tracking-tight">HR Copilot</span>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="relative grid min-h-screen bg-background lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      {/*
       * Dark theme: the panel has no fill of its own. The glow lives on the page and fades out
       * radially before the column boundary, so there is no seam between the two halves.
       */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 hidden bg-[radial-gradient(45%_70%_at_12%_0%,oklch(0.49_0.19_268/0.32),transparent_100%),radial-gradient(35%_50%_at_0%_100%,oklch(0.55_0.15_220/0.14),transparent_100%)] lg:dark:block"
      />

      {/* Light theme: a navy brand panel against the light form side, a deliberate split. */}
      <section className="relative hidden flex-col justify-between overflow-hidden bg-sidebar p-12 text-white lg:flex dark:bg-transparent">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_20%_0%,oklch(0.49_0.19_268/0.55),transparent_70%),radial-gradient(50%_40%_at_100%_100%,oklch(0.55_0.15_220/0.25),transparent_70%)] dark:hidden"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] [background-size:48px_48px] [mask-image:radial-gradient(70%_60%_at_30%_30%,black,transparent)]"
        />

        <Logo className="relative" />

        <div className="relative max-w-md space-y-10">
          <div className="space-y-4">
            <p className="text-sm font-medium tracking-wide text-indigo-200 uppercase">
              People operations, secured
            </p>
            <h1 className="text-4xl leading-tight font-semibold tracking-tight text-balance">
              Answers about your people, without the risk.
            </h1>
          </div>
          <ul className="space-y-6">
            {HIGHLIGHTS.map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex gap-4">
                <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <Icon className="size-5 text-indigo-100" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="font-medium">{title}</p>
                  <p className="text-sm leading-relaxed text-white/65">{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/75">Demo environment · all data is synthetic.</p>
      </section>

      <section className="relative flex items-center justify-center px-4 py-10 sm:px-12">
        <div className="w-full max-w-md space-y-8">
          <Logo className="lg:hidden" />
          <div className="space-y-2">
            <h2 className="text-3xl font-semibold tracking-tight">Welcome back</h2>
            <p className="text-sm text-muted-foreground">
              Sign in with your work account, or pick a demo persona below.
            </p>
          </div>
          <LoginForm />
        </div>
      </section>
    </main>
  );
}
