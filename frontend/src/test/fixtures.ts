import type { Graph, Note, NoteSummary, Suggestion, Tag } from "@/lib/types";

export const NOW = "2026-10-17T10:00:00Z";

export function noteSummary(overrides: Partial<NoteSummary> = {}): NoteSummary {
  return { id: "n1", title: "Kubernetes notes", tags: [], created_at: NOW, updated_at: NOW, ...overrides };
}

export function note(overrides: Partial<Note> = {}): Note {
  return { ...noteSummary(), owner_id: "u1", body: "# Pods\nbody text", ...overrides };
}

export function tag(name: string, count = 1): Tag {
  return { id: `tag-${name}`, name, note_count: count };
}

export function suggestion(overrides: Partial<Suggestion> = {}): Suggestion {
  return {
    id: "s1",
    source_note: { id: "n1", title: "Kubernetes deployment" },
    target_note: { id: "n2", title: "Kubernetes rollouts" },
    similarity_score: 0.44,
    explanation: "Shared keywords: kubernetes, deployment (44% keyword overlap)",
    created_at: NOW,
    ...overrides,
  };
}

export function page<T>(items: T[], total = items.length) {
  return { items, total, limit: 20, offset: 0 };
}

export function graph(overrides: Partial<Graph> = {}): Graph {
  return {
    nodes: [
      { id: "a", owner_id: "u1", title: "Alpha", tags: ["x"], created_at: NOW, updated_at: NOW },
      { id: "b", owner_id: "u1", title: "Beta", tags: [], created_at: NOW, updated_at: NOW },
      { id: "c", owner_id: "u1", title: "Gamma", tags: [], created_at: NOW, updated_at: NOW },
    ],
    edges: [{ id: "e1", source: "a", target: "b", created_at: NOW }],
    total_nodes: 3,
    max_nodes: 500,
    is_capped: false,
    message: null,
    ...overrides,
  };
}
