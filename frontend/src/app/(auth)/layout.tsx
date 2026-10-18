import Link from "next/link";
import type { ReactNode } from "react";

import { Logo } from "@/components/ui/logo";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main id="main" className="relative flex min-h-screen flex-col items-center justify-center bg-bg-app px-4 py-10">
      {/* Subtle accent glow */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="h-96 w-96 rounded-full bg-accent opacity-5 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        <Link href="/" className="mb-8 flex items-center justify-center gap-3">
          <Logo className="h-8 w-8 text-accent" />
          <span className="text-2xl font-semibold text-text-primary">LinkNote</span>
        </Link>

        <div className="rounded-xl border border-border-subtle bg-bg-surface p-8 shadow-2xl">
          {children}
        </div>
      </div>
    </main>
  );
}
