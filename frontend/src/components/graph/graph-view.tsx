"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { TagFilter } from "@/components/notes/tag-filter";
import { EmptyState, ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { InvalidGraphError, neighbours, sanitizeGraph } from "@/lib/graph";
import type { Graph } from "@/lib/types";
import { cn } from "@/lib/utils";

// The canvas needs the browser (and is heavy), so it is loaded on the client only.
const GraphCanvas = dynamic(() => import("@/components/graph/graph-canvas"), {
  ssr: false,
  loading: () => <Loading>Loading graph…</Loading>,
});

/** The accessible equivalent of the canvas: every note, its tags, and what it is connected to. */
function GraphList({ graph }: { graph: Graph }) {
  const connections = useMemo(() => neighbours(graph), [graph]);
  const sorted = useMemo(() => [...graph.nodes].sort((a, b) => a.title.localeCompare(b.title)), [graph.nodes]);

  return (
    <ul id="graph-list" aria-label="Notes and their connections" className="divide-y divide-border rounded-md border border-border bg-surface">
      {sorted.map((node) => {
        const linked = connections.get(node.id) ?? [];
        return (
          <li key={node.id} className="p-4">
            <Link href={`/notes/${node.id}`} className="font-medium text-brand hover:underline">
              {node.title}
            </Link>
            {node.tags.length > 0 ? <span className="ml-2 text-xs text-ink-soft">{node.tags.join(", ")}</span> : null}
            <p className="mt-1 text-sm text-ink-soft">
              {linked.length === 0 ? (
                "Not connected to other notes."
              ) : (
                <>
                  Connected to:{" "}
                  {linked.map((other, index) => (
                    <span key={other.id}>
                      {index > 0 ? ", " : ""}
                      <Link href={`/notes/${other.id}`} className="text-brand hover:underline">
                        {other.title}
                      </Link>
                    </span>
                  ))}
                </>
              )}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

export function GraphView() {
  const router = useRouter();
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [view, setView] = useState<"graph" | "list">("graph");

  const tags = useQuery({ queryKey: ["tags"], queryFn: api.listTags });
  const graph = useQuery({
    queryKey: ["graph", selectedTags],
    queryFn: async () => sanitizeGraph(await api.getGraph(selectedTags)),
  });

  const data = graph.data;
  const canvasNodes = useMemo(() => data?.nodes.map((n) => ({ id: n.id, title: n.title })) ?? [], [data]);
  const canvasEdges = useMemo(() => data?.edges.map((e) => ({ source: e.source, target: e.target })) ?? [], [data]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Knowledge graph</h1>

      {tags.data ? <TagFilter tags={tags.data} selected={selectedTags} onChange={setSelectedTags} /> : null}

      {graph.isPending ? <Loading>Loading graph…</Loading> : null}
      {graph.isError ? (
        <ErrorNotice
          message={graph.error instanceof InvalidGraphError ? graph.error.message : describeError(graph.error)}
          onRetry={() => graph.refetch()}
        />
      ) : null}

      {data && data.nodes.length === 0 ? (
        <EmptyState title={selectedTags.length > 0 ? "No notes have all of those tags" : "Nothing to show yet"}>
          {selectedTags.length > 0 ? (
            "Remove a tag to widen the graph."
          ) : (
            <>
              Notes appear here once you <Link className="text-brand underline" href="/notes/new">write some</Link>; links appear
              when you accept suggestions.
            </>
          )}
        </EmptyState>
      ) : null}

      {data && data.nodes.length > 0 ? (
        <>
          {data.is_capped ? (
            <p role="status" className="rounded-md border border-border bg-surface p-3 text-sm">
              {data.message ?? `Showing ${data.nodes.length} of ${data.total_nodes} notes.`}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-ink-soft">
              {data.nodes.length} {data.nodes.length === 1 ? "note" : "notes"}, {data.edges.length}{" "}
              {data.edges.length === 1 ? "connection" : "connections"}
            </p>
            <div role="group" aria-label="View" className="flex rounded-md border border-border">
              {(["graph", "list"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={view === value}
                  onClick={() => setView(value)}
                  className={cn("px-3 py-1 text-sm capitalize", view === value ? "bg-brand text-brand-foreground" : "bg-surface")}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>

          {view === "graph" ? (
            <>
              <button
                type="button"
                className="sr-only focus:not-sr-only focus:underline"
                onClick={() => setView("list")}
              >
                Switch to the accessible list view
              </button>
              <div
                role="img"
                aria-label={`Interactive graph of ${data.nodes.length} notes and ${data.edges.length} connections. Select a note to open it. The list view offers the same information as text.`}
              >
                <GraphCanvas nodes={canvasNodes} edges={canvasEdges} onNodeClick={(id) => router.push(`/notes/${id}`)} />
              </div>
            </>
          ) : (
            <GraphList graph={data} />
          )}
        </>
      ) : null}
    </div>
  );
}
