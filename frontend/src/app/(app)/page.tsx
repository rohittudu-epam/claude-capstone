"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LandingPage } from "@/components/landing/landing-page";
import { Loading } from "@/components/ui/feedback";
import { ApiError, api } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });

  const authenticated = me.isSuccess;
  const unauthenticated = me.error instanceof ApiError && me.error.status === 401;

  useEffect(() => {
    if (authenticated) {
      router.replace("/notes");
    }
  }, [authenticated, router]);

  if (me.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app">
        <Loading>Loading…</Loading>
      </div>
    );
  }

  if (authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app">
        <Loading>Redirecting…</Loading>
      </div>
    );
  }

  if (unauthenticated) {
    return <LandingPage />;
  }

  // Error case (network failure, etc.) - show landing page
  return <LandingPage />;
}
