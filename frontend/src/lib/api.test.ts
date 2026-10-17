import { describe, expect, it, vi } from "vitest";

import { ApiError, api, onSessionExpired } from "@/lib/api";
import { mockFetch } from "@/test/utils";

describe("request", () => {
  it("sends credentials and JSON, and parses the response", async () => {
    const { fn, calls } = mockFetch({ "POST /api/notes": { status: 201, json: { id: "n1" } } });
    const created = await api.createNote({ title: "t", body: "b", tags: ["x"] });
    expect(created).toEqual({ id: "n1" });
    expect(calls[0]?.body).toEqual({ title: "t", body: "b", tags: ["x"] });
    expect(fn.mock.calls[0]?.[1]).toMatchObject({
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
    });
  });

  it("returns undefined for 204", async () => {
    mockFetch({ "DELETE /api/notes/n1": { status: 204 } });
    await expect(api.deleteNote("n1")).resolves.toBeUndefined();
  });

  it("builds query strings, skipping empty values", async () => {
    const { calls } = mockFetch({ "GET /api/notes/search": { json: { items: [] } } });
    await api.searchNotes("kube", { tags: ["a", "b"], limit: 20, offset: 0 });
    expect(calls[0]?.search.get("q")).toBe("kube");
    expect(calls[0]?.search.get("tags")).toBe("a,b");
    expect(calls[0]?.search.get("offset")).toBe("0");
    await api.searchNotes("kube", { tags: [] });
    expect(calls[1]?.search.has("tags")).toBe(false);
  });

  it("turns error responses into ApiError with detail, field errors and correlation id", async () => {
    mockFetch({
      "POST /api/notes": {
        status: 400,
        json: { detail: "Invalid request", errors: [{ field: "title", message: "required" }], correlation_id: "cid-1" },
      },
    });
    const error = await api.createNote({ title: "", body: "" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 400, detail: "Invalid request", correlationId: "cid-1" });
    expect((error as ApiError).fieldErrors).toEqual([{ field: "title", message: "required" }]);
  });

  it("survives a non-JSON error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>Bad gateway</html>", { status: 502, statusText: "Bad Gateway" })),
    );
    const error = await api.listTags().catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 502, detail: "Bad Gateway" });
  });

  it("reports an unreachable server as a network error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    const error = await api.listTags().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).isNetwork).toBe(true);
  });

  it("logs the failing path but never the query string", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    mockFetch({ "GET /api/notes/search": { status: 500, json: { detail: "boom", correlation_id: "c9" } } });
    await api.searchNotes("secret search words", {}).catch(() => {});
    const logged = spy.mock.calls.map((c) => String(c[0])).join("\n");
    expect(logged).toContain("/api/notes/search");
    expect(logged).not.toContain("secret search words");
    spy.mockRestore();
  });
});

describe("session refresh", () => {
  it("refreshes once on 401 and retries the original request", async () => {
    let attempts = 0;
    const { to } = mockFetch({
      "GET /api/tags": () => (++attempts === 1 ? { status: 401, json: { detail: "Not authenticated" } } : { json: [] }),
      "POST /api/auth/refresh": { json: { user_id: "u", expires_in: 900 } },
    });
    await expect(api.listTags()).resolves.toEqual([]);
    expect(to("POST", "/api/auth/refresh")).toHaveLength(1);
    expect(to("GET", "/api/tags")).toHaveLength(2);
  });

  it("shares a single refresh between concurrent 401s", async () => {
    let tags = 0;
    let links = 0;
    const { to } = mockFetch({
      "GET /api/tags": () => (++tags === 1 ? { status: 401, json: {} } : { json: [] }),
      "GET /api/links": () => (++links === 1 ? { status: 401, json: {} } : { json: { items: [] } }),
      "POST /api/auth/refresh": { json: {} },
    });
    await Promise.all([api.listTags(), api.listLinks()]);
    expect(to("POST", "/api/auth/refresh")).toHaveLength(1);
  });

  it("signals session expiry and throws when the refresh fails", async () => {
    mockFetch({
      "GET /api/tags": { status: 401, json: { detail: "Not authenticated" } },
      "POST /api/auth/refresh": { status: 401, json: { detail: "Authentication failed" } },
    });
    const listener = vi.fn();
    const off = onSessionExpired(listener);
    await expect(api.listTags()).rejects.toMatchObject({ status: 401 });
    expect(listener).toHaveBeenCalledTimes(1);
    off();
  });

  it("does not try to refresh for the auth endpoints themselves", async () => {
    const { to } = mockFetch({ "POST /api/auth/login": { status: 401, json: { detail: "Authentication failed" } } });
    await expect(api.login({ email: "a@b.c", password: "x" })).rejects.toMatchObject({ status: 401 });
    expect(to("POST", "/api/auth/refresh")).toHaveLength(0);
  });
});
