"use client";

import { FileText, GitFork, Network } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { Logo } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: ReactNode;
  userEmail: string;
}

const NAV_ITEMS = [
  { href: "/notes", label: "Notes", icon: FileText },
  { href: "/suggestions", label: "Suggestions", icon: GitFork },
  { href: "/graph", label: "Graph", icon: Network },
];

export function AppShell({ children, userEmail }: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  async function signOut() {
    try {
      await api.logout();
    } finally {
      queryClient.clear();
      router.replace("/login");
    }
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg-app sm:flex-row">
      {/* Left Icon Rail - Hidden on mobile */}
      <aside className="hidden w-14 flex-col items-center border-r border-border-subtle bg-bg-surface py-4 sm:flex">
        <Link
          href="/notes"
          className="mb-6 flex h-9 w-9 items-center justify-center text-accent transition-opacity hover:opacity-80"
          aria-label="LinkNote home"
          title="LinkNote"
        >
          <Logo className="h-6 w-6" />
        </Link>

        <nav aria-label="Main navigation" className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                title={item.label}
                aria-label={item.label}
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-150",
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-text-secondary hover:bg-bg-hover hover:text-text-primary",
                )}
              >
                <Icon className="h-4 w-4" strokeWidth={1.5} />
                <span className="sr-only">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="flex flex-col items-center gap-3">
          <ThemeToggle />
          <button
            onClick={signOut}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-accent text-xs font-mono font-semibold transition-opacity hover:opacity-80"
            title={`Signed in as ${userEmail}`}
            aria-label="User menu"
          >
            {userEmail[0]?.toUpperCase() ?? "?"}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main id="main" className="flex flex-1 overflow-hidden pb-16 sm:pb-0">
        {children}
      </main>

      {/* Bottom Tab Bar - Visible on mobile only */}
      <nav
        aria-label="Main navigation"
        className="fixed bottom-0 left-0 right-0 z-30 flex items-center justify-around border-t border-border-subtle bg-bg-surface pb-safe sm:hidden"
      >
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              aria-label={item.label}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-2 transition-colors duration-150",
                isActive ? "text-accent" : "text-text-secondary",
              )}
            >
              <Icon className="h-5 w-5" strokeWidth={1.5} />
              <span className="text-xs font-medium">{item.label}</span>
            </Link>
          );
        })}
        <button
          onClick={signOut}
          aria-label={`Signed in as ${userEmail}`}
          className="flex flex-1 flex-col items-center gap-1 py-2 text-text-secondary transition-colors duration-150"
        >
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-accent-soft text-accent text-[10px] font-mono font-semibold">
            {userEmail[0]?.toUpperCase() ?? "?"}
          </div>
          <span className="text-xs font-medium">Account</span>
        </button>
      </nav>
    </div>
  );
}
