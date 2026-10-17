import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GraphView } from "@/components/graph/graph-view";
import { graph, tag } from "@/test/fixtures";
import { router } from "@/test/navigation-mock";
import { mockFetch, renderWithClient } from "@/test/utils";

vi.mock("next/navigation", async () => (await import("@/test/navigation-mock")).navigationModule);

// jsdom has no canvas; the stand-in exposes what the real one is given and lets tests click nodes.
vi.mock("@/components/graph/graph-canvas", () => ({
  default: ({
    nodes,
    edges,
    onNodeClick,
  }: {
    nodes: { id: string; title: string }[];
    edges: unknown[];
    onNodeClick: (id: string) => void;
  }) => (
    <div data-testid="graph-canvas" data-nodes={nodes.length} data-edges={edges.length}>
      {nodes.map((n) => (
        <button key={n.id} onClick={() => onNodeClick(n.id)}>
          canvas node {n.title}
        </button>
      ))}
    </div>
  ),
}));

const TAGS = { "GET /api/tags": { json: [tag("x", 1), tag("y", 1)] } };

describe("GraphView", () => {
  it("shows loading, then renders notes as nodes and links as edges", async () => {
    mockFetch({ ...TAGS, "GET /api/graph": { json: graph() } });
    renderWithClient(<GraphView />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading graph…");
    const canvas = await screen.findByTestId("graph-canvas");
    expect(canvas).toHaveAttribute("data-nodes", "3");
    expect(canvas).toHaveAttribute("data-edges", "1");
    expect(screen.getByText("3 notes, 1 connection")).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAccessibleName(/3 notes and 1 connections/);
  });

  it("opens the note when a node is selected", async () => {
    mockFetch({ ...TAGS, "GET /api/graph": { json: graph() } });
    const user = userEvent.setup();
    renderWithClient(<GraphView />);
    await user.click(await screen.findByRole("button", { name: "canvas node Beta" }));
    expect(router.push).toHaveBeenCalledWith("/notes/b");
  });

  it("re-queries the backend with the selected tags", async () => {
    const { to } = mockFetch({
      ...TAGS,
      "GET /api/graph": (req) => ({ json: req.search.get("tags") === "x" ? graph({ nodes: graph().nodes.slice(0, 1), edges: [] }) : graph() }),
    });
    const user = userEvent.setup();
    renderWithClient(<GraphView />);
    await screen.findByTestId("graph-canvas");
    await user.click(screen.getByRole("button", { name: /^x/ }));
    await waitFor(() => expect(screen.getByTestId("graph-canvas")).toHaveAttribute("data-nodes", "1"));
    expect(to("GET", "/api/graph").at(-1)?.search.get("tags")).toBe("x");
  });

  it("says when the graph is empty, and when a tag filter leaves nothing", async () => {
    const empty = graph({ nodes: [], edges: [], total_nodes: 0 });
    mockFetch({ ...TAGS, "GET /api/graph": { json: empty } });
    const user = userEvent.setup();
    renderWithClient(<GraphView />);
    expect(await screen.findByText("Nothing to show yet")).toBeInTheDocument();
    expect(screen.queryByTestId("graph-canvas")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^x/ }));
    expect(await screen.findByText("No notes have all of those tags")).toBeInTheDocument();
  });

  it("announces when the graph was capped", async () => {
    mockFetch({
      ...TAGS,
      "GET /api/graph": {
        json: graph({ is_capped: true, total_nodes: 900, max_nodes: 3, message: "Showing the 3 most recently updated of 900 matching notes." }),
      },
    });
    renderWithClient(<GraphView />);
    const banner = await screen.findByText(/Showing the 3 most recently updated of 900/);
    expect(banner).toHaveAttribute("role", "status");
  });

  it("shows an error with retry when the API fails, without crashing", async () => {
    let calls = 0;
    mockFetch({
      ...TAGS,
      "GET /api/graph": () => (++calls === 1 ? { status: 503, json: { detail: "down" } } : { json: graph() }),
    });
    const user = userEvent.setup();
    renderWithClient(<GraphView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("having trouble");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByTestId("graph-canvas")).toBeInTheDocument();
  });

  it("treats malformed graph data as an error and cleans up inconsistent data", async () => {
    mockFetch({ ...TAGS, "GET /api/graph": { json: { nodes: "oops" } } });
    const { unmount } = renderWithClient(<GraphView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("not in the expected format");
    unmount();

    const messy = graph();
    mockFetch({
      ...TAGS,
      "GET /api/graph": {
        json: { ...messy, edges: [...messy.edges, { id: "bad", source: "a", target: "ghost", created_at: "" }] },
      },
    });
    renderWithClient(<GraphView />);
    expect(await screen.findByTestId("graph-canvas")).toHaveAttribute("data-edges", "1");
  });

  it("offers a keyboard-friendly list with the same information", async () => {
    mockFetch({ ...TAGS, "GET /api/graph": { json: graph() } });
    const user = userEvent.setup();
    renderWithClient(<GraphView />);
    await screen.findByTestId("graph-canvas");
    await user.click(screen.getByRole("button", { name: "list" }));
    expect(screen.queryByTestId("graph-canvas")).not.toBeInTheDocument();

    const list = screen.getByRole("list", { name: "Notes and their connections" });
    const alpha = within(list).getAllByRole("listitem")[0] as HTMLElement;
    expect(within(alpha).getByRole("link", { name: "Alpha" })).toHaveAttribute("href", "/notes/a");
    expect(alpha).toHaveTextContent("Connected to: Beta");
    expect(within(list).getAllByRole("listitem")[2]).toHaveTextContent("Not connected to other notes.");

    await user.click(screen.getByRole("button", { name: "graph" }));
    expect(screen.getByTestId("graph-canvas")).toBeInTheDocument();
  });

  it("provides a skip control to the list view for assistive technology users", async () => {
    mockFetch({ ...TAGS, "GET /api/graph": { json: graph() } });
    const user = userEvent.setup();
    renderWithClient(<GraphView />);
    await screen.findByTestId("graph-canvas");
    await user.click(screen.getByRole("button", { name: "Switch to the accessible list view" }));
    expect(screen.getByRole("list", { name: "Notes and their connections" })).toBeInTheDocument();
  });
});
