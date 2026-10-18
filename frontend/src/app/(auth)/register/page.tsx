"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { RegisterForm } from "@/components/auth/register-form";
import { Loading } from "@/components/ui/feedback";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });

  useEffect(() => {
    if (me.isSuccess) {
      router.replace("/notes");
    }
  }, [me.isSuccess, router]);

  if (me.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app">
        <Loading>Loading…</Loading>
      </div>
    );
  }

  if (me.isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-app">
        <Loading>Redirecting…</Loading>
      </div>
    );
  }

  return <RegisterForm />;
}
