"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
import { ApiError, api, onSessionExpired } from "@/lib/api";

/**
 * Renders the app only for a signed-in user. Pages fetch their own data from the API, which enforces
 * authentication itself, so nothing private is ever in the HTML this gate protects.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });

  const unauthenticated = me.error instanceof ApiError && me.error.status === 401;

  useEffect(() => {
    if (unauthenticated) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [unauthenticated, router, pathname]);

  useEffect(
    () =>
      onSessionExpired(() => {
        queryClient.clear();
        router.replace(`/login?expired=1&next=${encodeURIComponent(pathname)}`);
      }),
    [queryClient, router, pathname],
  );

  if (me.isPending || unauthenticated) return <Loading>Checking your session…</Loading>;
  if (me.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app p-6">
        <div className="w-full max-w-lg">
          <ErrorNotice message={describeError(me.error)} onRetry={() => me.refetch()} />
        </div>
      </div>
    );
  }

  return <AppShell userEmail={me.data.email}>{children}</AppShell>;
}
