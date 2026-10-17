import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Only same-site relative paths are allowed as post-login destinations (blocks open redirects). */
export function safeNextPath(value: string | null | undefined, fallback = "/notes"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return fallback;
  return value;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function normalizeTag(raw: string): string {
  return raw.toLowerCase().split(/\s+/).filter(Boolean).join(" ");
}
