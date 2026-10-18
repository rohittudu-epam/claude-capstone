import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";

import { ThemeProvider } from "@/components/ui/theme-provider";
import type { ReactElement } from "react";
import { vi } from "vitest";

export interface Req {
  method: string;
  path: string;
  search: URLSearchParams;
  body: unknown;
}
export interface Reply {
  status?: number;
  json?: unknown;
  headers?: Record<string, string>;
}
export type Handler = Reply | ((req: Req) => Reply | Promise<Reply>);

/** Replaces global fetch with a route table keyed "METHOD /path"; unmatched requests fail loudly. */
export function mockFetch(routes: Record<string, Handler>) {
  const calls: Req[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const req: Req = {
      method: (init?.method ?? "GET").toUpperCase(),
      path: url.pathname,
      search: url.searchParams,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    };
    calls.push(req);
    const handler = routes[`${req.method} ${req.path}`];
    if (!handler) return new Response(JSON.stringify({ detail: `unmocked ${req.method} ${req.path}` }), { status: 599 });
    const reply = typeof handler === "function" ? await handler(req) : handler;
    const status = reply.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(reply.json ?? {}), {
      status,
      headers: { "content-type": "application/json", ...reply.headers },
    });
  });
  vi.stubGlobal("fetch", fn);
  return { calls, fn, to: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path) };
}

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return {
    client,
    ...render(
      <ThemeProvider>
        <QueryClientProvider client={client}>{ui}</QueryClientProvider>
      </ThemeProvider>,
    ),
  };
}
