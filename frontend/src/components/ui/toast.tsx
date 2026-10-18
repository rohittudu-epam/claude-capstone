"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

type ToastKind = "success" | "error";
interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

export const TOAST_DURATION_MS = 3000;

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
}

const NOOP: ToastApi = { success: () => undefined, error: () => undefined };
const ToastContext = createContext<ToastApi>(NOOP);

/** Toasts for the current page; a no-op outside a provider so components stay testable on their own. */
export function useToast(): ToastApi {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((t) => t.id !== id)), []);

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, kind, message }]);
      // Errors persist until dismissed so they can't be missed.
      if (kind === "success") setTimeout(() => dismiss(id), TOAST_DURATION_MS);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(() => ({ success: (m) => push("success", m), error: (m) => push("error", m) }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4">
        <div role="status" aria-live="polite" className="contents">
          {toasts
            .filter((t) => t.kind === "success")
            .map((t) => (
              <ToastView key={t.id} toast={t} onClose={dismiss} />
            ))}
        </div>
        <div role="alert" className="contents">
          {toasts
            .filter((t) => t.kind === "error")
            .map((t) => (
              <ToastView key={t.id} toast={t} onClose={dismiss} />
            ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

function ToastView({ toast, onClose }: { toast: ToastItem; onClose: (id: number) => void }) {
  return (
    <div
      className={cn(
        "pointer-events-auto flex max-w-md items-center gap-3 rounded-lg border bg-surface px-4 py-2 text-sm shadow-lg",
        toast.kind === "success" ? "border-success" : "border-danger text-danger",
      )}
    >
      <span>{toast.message}</span>
      <button
        type="button"
        aria-label="Dismiss notification"
        className="ml-auto rounded px-1 text-ink-soft hover:text-ink"
        onClick={() => onClose(toast.id)}
      >
        ×
      </button>
    </div>
  );
}
