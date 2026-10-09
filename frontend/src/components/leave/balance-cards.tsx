import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LeaveBalance } from "@/lib/api/types";

export function BalanceCards({ balances }: { balances: LeaveBalance[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {balances.map((b) => {
        const allocated = Number(b.allocated);
        const used = Number(b.used);
        const pending = Number(b.pending);
        const pct = (n: number) => `${allocated ? Math.min(100, (n / allocated) * 100) : 0}%`;
        return (
          <Card key={b.leave_type.id}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {b.leave_type.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="tabular text-3xl font-semibold tracking-tight">
                {Number(b.remaining)}
                <span className="text-base font-normal text-muted-foreground"> / {allocated} left</span>
              </p>
              <div
                className="flex h-2 overflow-hidden rounded-full bg-muted"
                role="img"
                aria-label={`${used} used, ${pending} pending of ${allocated} days`}
              >
                <div className="bg-primary" style={{ width: pct(used) }} />
                <div className="bg-amber-400" style={{ width: pct(pending) }} />
              </div>
              <p className="text-xs text-muted-foreground">
                {used} used · {pending} pending
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
