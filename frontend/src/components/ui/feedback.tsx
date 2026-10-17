import * as React from "react";

import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function Loading({ children = "Loading…" }: { children?: React.ReactNode }) {
  return (
    <p role="status" className="py-8 text-center text-ink-soft">
      {children}
    </p>
  );
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-md border border-danger bg-surface p-4 text-danger">
      <p>{message}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-surface p-8 text-center">
      <p className="font-medium">{title}</p>
      {children ? <div className="mt-2 text-sm text-ink-soft">{children}</div> : null}
    </div>
  );
}

/** Turns any failure into text for the user, with the support reference when the server sent one. */
export function describeError(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof ApiError) {
    if (error.isNetwork) return error.detail;
    if (error.status >= 500) {
      const reference = error.correlationId ? ` (reference ${error.correlationId})` : "";
      return `The service is having trouble right now${reference}. Please try again in a moment.`;
    }
    return error.detail || fallback;
  }
  return fallback;
}

export function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-ink-soft">{children}</span>;
}
