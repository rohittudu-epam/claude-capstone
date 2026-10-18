"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { describeError } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/field";
import { ApiError, api } from "@/lib/api";

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/;
const MIN_PASSWORD_LENGTH = 8;
const MAX_PASSWORD_BYTES = 72; // bcrypt ignores anything longer, so the server rejects it

type Errors = { email?: string; password?: string; confirm?: string };

export function RegisterForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): Errors {
    const next: Errors = {};
    if (!EMAIL_PATTERN.test(email.trim())) next.email = "Enter a valid email address.";
    if (password.length < MIN_PASSWORD_LENGTH) next.password = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
    else if (new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES) {
      next.password = `Use at most ${MAX_PASSWORD_BYTES} bytes (long passwords with special characters count extra).`;
    }
    if (confirm !== password) next.confirm = "The passwords do not match.";
    return next;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const next = validate();
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await api.register({ email: email.trim(), password });
      await api.login({ email: email.trim(), password });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      router.push("/notes");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setErrors({ email: "An account with this email already exists." });
      } else if (error instanceof ApiError && error.status === 400 && error.fieldErrors.length > 0) {
        setFormError(error.fieldErrors.map((e) => e.message).join(" "));
      } else {
        setFormError(describeError(error));
      }
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5" aria-labelledby="register-title">
      <div className="text-center">
        <h1 id="register-title" className="text-xl font-semibold text-text-primary">
          Create your account
        </h1>
        <p className="mt-1 text-sm text-text-secondary">Start building your knowledge graph</p>
      </div>

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

      <Field id="password" label="Password" error={errors.password} hint={`At least ${MIN_PASSWORD_LENGTH} characters`}>
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        )}
      </Field>

      <Field id="confirm" label="Confirm password" error={errors.confirm}>
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        )}
      </Field>

      <Button type="submit" className="w-full" loading={submitting}>
        Create account
      </Button>

      <p className="text-center text-sm text-text-secondary">
        Already registered?{" "}
        <Link className="text-accent underline hover:opacity-80" href="/login">
          Sign in
        </Link>
      </p>
    </form>
  );
}
