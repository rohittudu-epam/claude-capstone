import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-lg border border-border-strong bg-bg-elevated px-3 py-2 text-sm text-text-primary",
        "placeholder:text-text-secondary",
        "focus-visible:border-accent focus-visible:shadow-[0_0_0_3px_rgba(255,90,54,0.25)] focus-visible:outline-none",
        "aria-[invalid=true]:border-danger",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-all duration-150 ease-out",
        className,
      )}
      ref={ref}
      {...props}
    />
  );
});

Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[280px] w-full rounded-lg border border-border-strong bg-bg-elevated px-3 py-3 text-sm leading-relaxed text-text-primary",
        "placeholder:text-text-secondary",
        "focus-visible:border-accent focus-visible:shadow-[0_0_0_3px_rgba(255,90,54,0.25)] focus-visible:outline-none",
        "aria-[invalid=true]:border-danger",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-all duration-150 ease-out",
        "resize-y font-mono",
        className,
      )}
      ref={ref}
      {...props}
    />
  );
});

Textarea.displayName = "Textarea";
