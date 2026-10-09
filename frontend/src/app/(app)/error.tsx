"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

// Never shows stack traces; the digest correlates with server logs (NFR-08).
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="size-6 text-destructive" aria-hidden />
      </span>
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">We couldn&apos;t load this page</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          You may not have access to this information, or the service is temporarily unavailable.
        </p>
        {error.digest && (
          <p className="font-mono text-xs text-muted-foreground">Reference: {error.digest}</p>
        )}
      </div>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
