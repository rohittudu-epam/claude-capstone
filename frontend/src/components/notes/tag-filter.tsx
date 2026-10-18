"use client";

import { X } from "lucide-react";
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

  const selectedTags = tags.filter((tag) => selected.includes(tag.name));
  const unselectedTags = tags.filter((tag) => !selected.includes(tag.name));

  return (
    <div role="group" aria-label="Filter by tags" className="space-y-2">
      {selectedTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedTags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() => toggle(tag.name)}
              className="inline-flex items-center gap-1.5 rounded-md border border-accent-border bg-accent-soft px-2.5 py-1 text-xs font-mono font-medium text-accent transition-all duration-150 hover:bg-accent hover:text-white"
            >
              {tag.name}
              <X className="h-3 w-3" strokeWidth={2} />
            </button>
          ))}
        </div>
      )}

      {unselectedTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {unselectedTags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() => toggle(tag.name)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border-subtle bg-bg-elevated px-2.5 py-1 text-xs font-mono text-text-secondary transition-all duration-150 hover:border-border-strong hover:bg-bg-hover hover:text-text-primary"
            >
              {tag.name}
              <span className="opacity-70">({tag.note_count})</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
