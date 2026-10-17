"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
import { ApiError, api, onSessionExpired } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/notes", label: "Notes" },
  { href: "/suggestions", label: "Suggestions" },
  { href: "/graph", label: "Graph" },
];

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

  async function signOut() {
    try {
      await api.logout();
    } finally {
      queryClient.clear();
      router.replace("/login");
    }
  }

  if (me.isPending || unauthenticated) return <Loading>Checking your session…</Loading>;
  if (me.isError) {
    return (
      <div className="mx-auto max-w-lg p-6">
        <ErrorNotice message={describeError(me.error)} onRetry={() => me.refetch()} />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <span className="font-semibold">LinkNote</span>
          <nav aria-label="Main" className="flex gap-1">
            {NAV.map((item) => {
              const current = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={current ? "page" : undefined}
                  className={cn("rounded-md px-3 py-1.5 text-sm", current ? "bg-muted font-medium" : "hover:bg-muted")}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-ink-soft">{me.data.email}</span>
            <Button variant="secondary" size="sm" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-5xl px-4 py-6">
        {children}
      </main>
    </div>
  );
}
