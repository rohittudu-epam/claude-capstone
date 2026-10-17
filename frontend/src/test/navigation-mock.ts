import { vi } from "vitest";

/** Shared stand-in for next/navigation. Use: vi.mock("next/navigation", async () => (await import("@/test/navigation-mock")).navigationModule) */
export const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() };
export const state = { pathname: "/notes", search: "" };

export const navigationModule = {
  useRouter: () => router,
  usePathname: () => state.pathname,
  useSearchParams: () => new URLSearchParams(state.search),
  redirect: vi.fn(),
};
