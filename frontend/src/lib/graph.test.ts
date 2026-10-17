import { describe, expect, it } from "vitest";

import { InvalidGraphError, neighbours, sanitizeGraph } from "@/lib/graph";
import { graph } from "@/test/fixtures";

describe("sanitizeGraph", () => {
  it("passes a consistent graph through", () => {
    const g = sanitizeGraph(graph());
    expect(g.nodes).toHaveLength(3);
    expect(g.edges).toHaveLength(1);
  });

  it.each([null, undefined, "x", {}, { nodes: [] }, { nodes: "no", edges: [] }, { nodes: [], edges: {} }])(
    "rejects malformed payload %j",
    (payload) => {
      expect(() => sanitizeGraph(payload)).toThrow(InvalidGraphError);
    },
  );

  it("drops dangling edges, self loops, duplicates and malformed entries", () => {
    const base = graph();
    const g = sanitizeGraph({
      ...base,
      nodes: [...base.nodes, base.nodes[0], { id: 5 }, null],
      edges: [
        ...base.edges,
        { id: "dup", source: "b", target: "a", created_at: "" },
        { id: "loop", source: "a", target: "a", created_at: "" },
        { id: "dangling", source: "a", target: "zzz", created_at: "" },
        { id: "bad" },
      ],
    });
    expect(g.nodes.map((n) => n.id)).toEqual(["a", "b", "c"]);
    expect(g.edges.map((e) => e.id)).toEqual(["e1"]);
  });
});

describe("neighbours", () => {
  it("lists linked notes from both ends, ordered by title", () => {
    const base = graph();
    const g = { ...base, edges: [...base.edges, { id: "e2", source: "c", target: "a", created_at: "" }] };
    const result = neighbours(g);
    expect(result.get("a")?.map((n) => n.title)).toEqual(["Beta", "Gamma"]);
    expect(result.get("b")?.map((n) => n.title)).toEqual(["Alpha"]);
  });

  it("gives unconnected notes an empty list", () => {
    expect(neighbours(graph()).get("c")).toEqual([]);
  });
});
