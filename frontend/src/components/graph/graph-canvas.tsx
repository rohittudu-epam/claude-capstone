"use client";

import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";
import { useEffect, useMemo, useRef, useState } from "react";

export interface CanvasNode {
  id: string;
  title: string;
}
export interface CanvasEdge {
  source: string;
  target: string;
}

const HEIGHT = 512;
const NODE_RADIUS = 5;
const LABEL_ALWAYS_BELOW = 30; // draw every label for small graphs; larger ones label on zoom

function cssColor(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function truncate(text: string, max = 28): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/** The interactive canvas. Loaded client-side only (it needs the DOM); see GraphView. */
export default function GraphCanvas({
  nodes,
  edges,
  onNodeClick,
}: {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  onNodeClick: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const graph = useRef<ForceGraphMethods | undefined>(undefined);
  const [width, setWidth] = useState(800);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    setWidth(element.clientWidth || 800);
    const observer = new ResizeObserver(([entry]) => entry && setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // The library mutates the objects it is given (adds coordinates, swaps ids for node objects), so hand it copies.
  const data = useMemo(
    () => ({
      nodes: nodes.map((n) => ({ id: n.id, name: n.title })),
      links: edges.map((e) => ({ source: e.source, target: e.target })),
    }),
    [nodes, edges],
  );

  const brand = cssColor("--color-brand", "#4f46e5");
  const ink = cssColor("--color-ink", "#111827");
  const border = cssColor("--color-border", "#d1d5db");

  return (
    <div ref={container} className="w-full overflow-hidden rounded-md border border-border bg-surface" style={{ height: HEIGHT }}>
      <ForceGraph2D
        ref={graph}
        graphData={data}
        width={width}
        height={HEIGHT}
        nodeId="id"
        nodeLabel="name"
        linkColor={() => border}
        cooldownTicks={120}
        onEngineStop={() => graph.current?.zoomToFit(300, 40)}
        onNodeClick={(node) => onNodeClick(String(node.id))}
        nodeCanvasObject={(node, ctx, scale) => {
          const x = node.x ?? 0;
          const y = node.y ?? 0;
          ctx.beginPath();
          ctx.arc(x, y, NODE_RADIUS, 0, 2 * Math.PI);
          ctx.fillStyle = brand;
          ctx.fill();
          if (nodes.length <= LABEL_ALWAYS_BELOW || scale > 1.5) {
            ctx.font = `${12 / scale}px sans-serif`;
            ctx.textAlign = "center";
            ctx.fillStyle = ink;
            ctx.fillText(truncate(String(node.name)), x, y + NODE_RADIUS + 9 / scale);
          }
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, NODE_RADIUS + 3, 0, 2 * Math.PI);
          ctx.fill();
        }}
      />
    </div>
  );
}
