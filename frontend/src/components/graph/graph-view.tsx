"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { List, Network } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Sidebar, SidebarHeader, SidebarSection, SidebarSectionLabel, SidebarHintBar } from "@/components/layout/sidebar";
import { TagFilter } from "@/components/notes/tag-filter";
import { KeyCap } from "@/components/ui/key-cap";
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
    <ul id="graph-list" aria-label="Notes and their connections" className="space-y-3">
      {sorted.map((node) => {
        const linked = connections.get(node.id) ?? [];
        return (
          <li key={node.id} className="rounded-xl border border-border-subtle bg-bg-surface p-4">
            <Link href={`/notes/${node.id}`} className="font-mono text-base font-semibold text-accent hover:underline">
              {node.title}
            </Link>
            {node.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {node.tags.map((tag) => (
                  <span key={tag} className="rounded border border-border-strong bg-bg-elevated px-2 py-0.5 text-xs font-mono text-text-secondary">
                    {tag}
                  </span>
                ))}
              </div>
            )}
            <p className="mt-2 text-sm text-text-secondary">
              {linked.length === 0 ? (
                "Not connected to other notes"
              ) : (
                <>
                  <span className="text-text-muted">Connected to: </span>
                  {linked.map((other, index) => (
                    <span key={other.id}>
                      {index > 0 && <span className="text-text-muted">, </span>}
                      <Link href={`/notes/${other.id}`} className="font-mono text-accent hover:underline">
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
    <>
      {/* Sidebar */}
      <Sidebar>
        <SidebarHeader>
          <h2 className="font-mono text-sm font-semibold text-text-primary">Knowledge Graph</h2>
        </SidebarHeader>

        {tags.data && tags.data.length > 0 && (
          <SidebarSection>
            <SidebarSectionLabel>Filters</SidebarSectionLabel>
            <TagFilter tags={tags.data} selected={selectedTags} onChange={setSelectedTags} />
          </SidebarSection>
        )}

        {data && data.nodes.length > 0 && (
          <SidebarSection>
            <SidebarSectionLabel>Stats</SidebarSectionLabel>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Notes</span>
                <span className="font-mono text-text-primary">{data.nodes.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Connections</span>
                <span className="font-mono text-text-primary">{data.edges.length}</span>
              </div>
              {data.is_capped && (
                <div className="mt-3 rounded-lg border border-warning/30 bg-warning/10 p-2 text-xs text-warning">
                  {data.message ?? `Showing ${data.nodes.length} of ${data.total_nodes} notes`}
                </div>
              )}
            </div>
          </SidebarSection>
        )}

        <div className="flex-1" />
        <SidebarHintBar>
          <span>
            <KeyCap>Click</KeyCap> node to open
          </span>
          <span>
            <KeyCap>F</KeyCap> fit
          </span>
        </SidebarHintBar>
      </Sidebar>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <PageHeader
          title="Knowledge Graph"
          badge={view === "graph" ? "Graph view" : "List view"}
          description="Visual connections between your notes"
          actions={
            <div className="flex gap-2">
              <div role="group" aria-label="View mode" className="flex rounded-lg border border-border-strong overflow-hidden">
                <button
                  type="button"
                  aria-pressed={view === "graph"}
                  onClick={() => setView("graph")}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 text-sm transition-colors",
                    view === "graph" ? "bg-accent text-white" : "bg-bg-surface text-text-secondary hover:text-text-primary",
                  )}
                  title="Graph view"
                >
                  <Network className="h-4 w-4" strokeWidth={1.5} />
                  Graph
                </button>
                <button
                  type="button"
                  aria-pressed={view === "list"}
                  onClick={() => setView("list")}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 text-sm transition-colors border-l border-border-strong",
                    view === "list" ? "bg-accent text-white" : "bg-bg-surface text-text-secondary hover:text-text-primary",
                  )}
                  title="List view"
                >
                  <List className="h-4 w-4" strokeWidth={1.5} />
                  List
                </button>
              </div>
            </div>
          }
        />

        <div className="flex-1 overflow-hidden bg-bg-app">
          {graph.isPending ? (
            <div className="flex h-full items-center justify-center">
              <Loading>Loading graph…</Loading>
            </div>
          ) : null}

          {graph.isError ? (
            <div className="flex h-full items-center justify-center p-6">
              <ErrorNotice
                message={graph.error instanceof InvalidGraphError ? graph.error.message : describeError(graph.error)}
                onRetry={() => graph.refetch()}
              />
            </div>
          ) : null}

          {data && data.nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6">
              <EmptyState title={selectedTags.length > 0 ? "No notes have all of those tags" : "Nothing to show yet"}>
                {selectedTags.length > 0 ? (
                  "Remove a tag to widen the graph."
                ) : (
                  <>
                    Notes appear here once you <Link className="text-accent underline" href="/notes/new">write some</Link>; links
                    appear when you accept suggestions.
                  </>
                )}
              </EmptyState>
            </div>
          ) : null}

          {data && data.nodes.length > 0 ? (
            view === "graph" ? (
              <div className="relative h-full w-full">
                <button type="button" className="sr-only focus:not-sr-only focus:underline" onClick={() => setView("list")}>
                  Switch to the accessible list view
                </button>
                <div
                  role="img"
                  aria-label={`Interactive graph of ${data.nodes.length} notes and ${data.edges.length} connections. Select a note to open it. The list view offers the same information as text.`}
                  className="h-full w-full"
                >
                  <GraphCanvas nodes={canvasNodes} edges={canvasEdges} onNodeClick={(id) => router.push(`/notes/${id}`)} />
                </div>
              </div>
            ) : (
              <div className="h-full overflow-y-auto p-6">
                <GraphList graph={data} />
              </div>
            )
          ) : null}
        </div>
      </div>
    </>
  );
}
