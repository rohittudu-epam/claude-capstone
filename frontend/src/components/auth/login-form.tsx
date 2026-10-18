"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { describeError } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/field";
import { ApiError, api } from "@/lib/api";
import { safeNextPath } from "@/lib/utils";

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const next: typeof errors = {};
    if (!EMAIL_PATTERN.test(email.trim())) next.email = "Enter a valid email address.";
    if (!password) next.password = "Enter your password.";
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await api.login({ email: email.trim(), password });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      router.push(safeNextPath(params.get("next")));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError("Incorrect email or password.");
      } else if (error instanceof ApiError && error.status === 429) {
        setFormError("Too many attempts. Wait a minute, then try again.");
      } else {
        setFormError(describeError(error));
      }
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5" aria-labelledby="login-title">
      <div className="text-center">
        <h1 id="login-title" className="text-xl font-semibold text-text-primary">
          Sign in
        </h1>
        <p className="mt-1 text-sm text-text-secondary">Welcome back to your knowledge graph</p>
      </div>

      {params.get("expired") && (
        <div role="status" className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
          Your session expired. Please sign in again.
        </div>
      )}

      {formError && (
        <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {formError}
        </div>
      )}

      <Field id="email" label="Email" error={errors.email}>
        {(props) => (
          <Input {...props} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        )}
      </Field>

      <Field id="password" label="Password" error={errors.password}>
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        )}
      </Field>

      <Button type="submit" className="w-full" loading={submitting}>
        Sign in
      </Button>

      <p className="text-center text-sm text-text-secondary">
        No account yet?{" "}
        <Link className="text-accent underline hover:opacity-80" href="/register">
          Create one
        </Link>
      </p>
    </form>
  );
}
