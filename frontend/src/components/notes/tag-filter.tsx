"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Tag } from "@/lib/types";

/** Toggle chips for filtering by tags. Selecting several narrows results to notes that have all of them. */
export function TagFilter({
  tags,
  selected,
  onChange,
}: {
  tags: Tag[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  if (tags.length === 0) return null;

  function toggle(name: string) {
    onChange(selected.includes(name) ? selected.filter((t) => t !== name) : [...selected, name]);
  }

  return (
    <div role="group" aria-label="Filter by tags" className="flex flex-wrap items-center gap-2">
      {tags.map((tag) => {
        const active = selected.includes(tag.name);
        return (
          <button
            key={tag.id}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(tag.name)}
            className={cn(
              "rounded-full border px-3 py-1 text-sm",
              active ? "border-brand bg-brand text-brand-foreground" : "border-border bg-surface hover:bg-muted",
            )}
          >
            {active ? <span aria-hidden="true">✓ </span> : null}
            {tag.name} <span className="opacity-70">({tag.note_count})</span>
          </button>
        );
      })}
      {selected.length > 0 ? (
        <Button variant="ghost" size="sm" onClick={() => onChange([])}>
          Clear filters
        </Button>
      ) : null}
    </div>
  );
}
