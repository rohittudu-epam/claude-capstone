import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SuggestionsList } from "@/components/suggestions/suggestions-list";
import { page, suggestion } from "@/test/fixtures";
import { mockFetch, renderWithClient } from "@/test/utils";

vi.mock("next/navigation", async () => (await import("@/test/navigation-mock")).navigationModule);

const TWO = page([
  suggestion({ id: "s1" }),
  suggestion({
    id: "s2",
    source_note: { id: "n3", title: "Python testing" },
    target_note: { id: "n4", title: "Pytest fixtures" },
    similarity_score: 0.31,
    explanation: "Shared keywords: pytest (31% keyword overlap)",
  }),
]);

const accept = (name: string) => screen.getByRole("button", { name: new RegExp(`Accept link between ${name}`) });
const reject = (name: string) => screen.getByRole("button", { name: new RegExp(`Reject link between ${name}`) });

describe("SuggestionsList", () => {
  it("shows what is needed to judge each suggestion", async () => {
    mockFetch({ "GET /api/suggestions": { json: TWO } });
    renderWithClient(<SuggestionsList />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading suggestions…");
    expect(await screen.findByRole("heading", { name: "Link suggestions (2)" })).toBeInTheDocument();
    const first = screen.getAllByRole("listitem")[0] as HTMLElement;
    expect(within(first).getByRole("link", { name: "Kubernetes deployment" })).toHaveAttribute("href", "/notes/n1");
    expect(within(first).getByRole("link", { name: "Kubernetes rollouts" })).toHaveAttribute("href", "/notes/n2");
    expect(first).toHaveTextContent("44% match");
    expect(first).toHaveTextContent("Shared keywords: kubernetes, deployment");
  });

  it("accepts a suggestion, removes it, confirms, and refreshes graph data", async () => {
    const { to } = mockFetch({
      "GET /api/suggestions": { json: TWO },
      "POST /api/suggestions/s1/accept": { status: 201, json: { id: "l1" } },
    });
    const user = userEvent.setup();
    const { client } = renderWithClient(<SuggestionsList />);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await screen.findByRole("heading", { name: "Link suggestions (2)" });

    await user.click(accept("Kubernetes deployment"));
    expect(await screen.findByText(/Linked “Kubernetes deployment” and “Kubernetes rollouts”/)).toBeInTheDocument();
    expect(to("POST", "/api/suggestions/s1/accept")).toHaveLength(1);
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "Link suggestions (1)" })).toBeInTheDocument();
    const keys = invalidate.mock.calls.map((c) => (c[0] as { queryKey: string[] }).queryKey[0]);
    expect(keys).toEqual(expect.arrayContaining(["graph", "links"]));
  });

  it("rejects a suggestion without touching the graph", async () => {
    const { to } = mockFetch({
      "GET /api/suggestions": { json: TWO },
      "POST /api/suggestions/s2/reject": { status: 204 },
    });
    const user = userEvent.setup();
    const { client } = renderWithClient(<SuggestionsList />);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await screen.findByRole("heading", { name: "Link suggestions (2)" });

    await user.click(reject("Python testing"));
    expect(await screen.findByText(/Dismissed the suggestion for “Python testing”/)).toBeInTheDocument();
    expect(to("POST", "/api/suggestions/s2/reject")).toHaveLength(1);
    expect(screen.queryByText("Python testing")).not.toBeInTheDocument();
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("ignores a second click while the first is still in flight", async () => {
    let release: () => void = () => {};
    const { to } = mockFetch({
      "GET /api/suggestions": { json: TWO },
      "POST /api/suggestions/s1/accept": () => new Promise((resolve) => (release = () => resolve({ status: 201, json: {} }))),
    });
    const user = userEvent.setup();
    renderWithClient(<SuggestionsList />);
    await screen.findByRole("heading", { name: "Link suggestions (2)" });

    await user.click(accept("Kubernetes deployment"));
    expect(await screen.findByRole("button", { name: /Accept link between Kubernetes deployment/ })).toBeDisabled();
    expect(reject("Kubernetes deployment")).toBeDisabled();
    await user.click(accept("Kubernetes deployment"));
    expect(to("POST", "/api/suggestions/s1/accept")).toHaveLength(1);
    release();
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(1));
  });

  it("explains and removes a suggestion that was already handled elsewhere", async () => {
    mockFetch({
      "GET /api/suggestions": { json: TWO },
      "POST /api/suggestions/s1/accept": { status: 404, json: { detail: "Suggestion not found" } },
    });
    const user = userEvent.setup();
    renderWithClient(<SuggestionsList />);
    await screen.findByRole("heading", { name: "Link suggestions (2)" });
    await user.click(accept("Kubernetes deployment"));
    expect(await screen.findByRole("status")).toHaveTextContent("already handled");
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("explains a stale suggestion and reloads the list", async () => {
    let loads = 0;
    mockFetch({
      "GET /api/suggestions": () => (++loads === 1 ? { json: TWO } : { json: page([suggestion({ id: "s1b" })]) }),
      "POST /api/suggestions/s1/accept": { status: 409, json: { detail: "Suggestion is stale" } },
    });
    const user = userEvent.setup();
    renderWithClient(<SuggestionsList />);
    await screen.findByRole("heading", { name: "Link suggestions (2)" });
    await user.click(accept("Kubernetes deployment"));
    expect(await screen.findByText(/one of those notes changed/i)).toBeInTheDocument();
    await waitFor(() => expect(loads).toBeGreaterThanOrEqual(2));
  });

  it("keeps the suggestion and shows the problem next to it when the service fails", async () => {
    mockFetch({
      "GET /api/suggestions": { json: TWO },
      "POST /api/suggestions/s1/accept": { status: 500, json: { detail: "boom", correlation_id: "ref-42" } },
    });
    const user = userEvent.setup();
    renderWithClient(<SuggestionsList />);
    await screen.findByRole("heading", { name: "Link suggestions (2)" });
    await user.click(accept("Kubernetes deployment"));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("reference ref-42");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(accept("Kubernetes deployment")).toBeEnabled();
  });

  it("shows an empty state, and an error with retry", async () => {
    mockFetch({ "GET /api/suggestions": { json: page([]) } });
    const { unmount } = renderWithClient(<SuggestionsList />);
    expect(await screen.findByText("No suggestions to review")).toBeInTheDocument();
    unmount();

    let calls = 0;
    mockFetch({
      "GET /api/suggestions": () => (++calls === 1 ? { status: 503, json: { detail: "down" } } : { json: TWO }),
    });
    const user = userEvent.setup();
    renderWithClient(<SuggestionsList />);
    await user.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Link suggestions (2)" })).toBeInTheDocument();
  });
});
