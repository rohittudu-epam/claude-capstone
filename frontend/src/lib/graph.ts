import type { Graph, GraphEdge, GraphNode } from "@/lib/types";

export class InvalidGraphError extends Error {
  constructor() {
    super("The graph data was not in the expected format.");
    this.name = "InvalidGraphError";
  }
}

function isNode(value: unknown): value is GraphNode {
  const node = value as Partial<GraphNode> | null;
  return typeof node?.id === "string" && typeof node.title === "string";
}

function isEdge(value: unknown): value is GraphEdge {
  const edge = value as Partial<GraphEdge> | null;
  return typeof edge?.source === "string" && typeof edge.target === "string";
}

/**
 * Defends the page against a malformed or inconsistent response: wrong shapes throw (shown as an error
 * state), while duplicate nodes, self-loops, repeated edges and edges to missing nodes are dropped so the
 * renderer never sees them.
 */
export function sanitizeGraph(raw: unknown): Graph {
  const graph = raw as Partial<Graph> | null;
  if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) throw new InvalidGraphError();

  const nodes = new Map<string, GraphNode>();
  for (const node of graph.nodes) {
    if (isNode(node) && !nodes.has(node.id)) nodes.set(node.id, { ...node, tags: Array.isArray(node.tags) ? node.tags : [] });
  }

  const seen = new Set<string>();
  const edges: GraphEdge[] = [];
  for (const edge of graph.edges) {
    if (!isEdge(edge) || edge.source === edge.target || !nodes.has(edge.source) || !nodes.has(edge.target)) continue;
    const key = [edge.source, edge.target].sort().join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    edges.push(edge);
  }

  return {
    nodes: [...nodes.values()],
    edges,
    total_nodes: typeof graph.total_nodes === "number" ? graph.total_nodes : nodes.size,
    max_nodes: typeof graph.max_nodes === "number" ? graph.max_nodes : nodes.size,
    is_capped: Boolean(graph.is_capped),
    message: typeof graph.message === "string" ? graph.message : null,
  };
}

/** For each node id, the nodes it is directly linked to, ordered by title. */
export function neighbours(graph: Graph): Map<string, GraphNode[]> {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const result = new Map<string, GraphNode[]>(graph.nodes.map((n) => [n.id, []]));
  for (const { source, target } of graph.edges) {
    const a = byId.get(source);
    const b = byId.get(target);
    if (a && b) {
      result.get(source)?.push(b);
      result.get(target)?.push(a);
    }
  }
  for (const list of result.values()) list.sort((x, y) => x.title.localeCompare(y.title));
  return result;
}
