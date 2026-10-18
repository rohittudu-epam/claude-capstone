"use client";

import { X } from "lucide-react";
import { useId, useState, type KeyboardEvent } from "react";

import { Input, Label } from "@/components/ui/field";
import { normalizeTag } from "@/lib/utils";

export const MAX_TAGS = 20;
export const MAX_TAG_LENGTH = 50;

export function TagInput({
  value,
  onChange,
  suggestions,
  error,
}: {
  value: string[];
  onChange: (tags: string[]) => void;
  suggestions: string[];
  error?: string | undefined;
}) {
  const id = useId();
  const [draft, setDraft] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  function commit() {
    const tag = normalizeTag(draft.replaceAll(",", " "));
    setDraft("");
    if (!tag || value.includes(tag)) return setLocalError(null);
    if (tag.length > MAX_TAG_LENGTH) return setLocalError(`Tags can be at most ${MAX_TAG_LENGTH} characters.`);
    if (value.length >= MAX_TAGS) return setLocalError(`A note can have at most ${MAX_TAGS} tags.`);
    setLocalError(null);
    onChange([...value, tag]);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault(); // Enter here adds a tag; it must not submit the note form
      commit();
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  const shownError = localError ?? error;
  const hintId = `${id}-hint`;

  return (
    <div>
      <Label htmlFor={`${id}-input`}>Tags</Label>
      {value.length > 0 && (
        <ul aria-label="Selected tags" className="mb-2 flex flex-wrap gap-2">
          {value.map((tag) => (
            <li
              key={tag}
              className="inline-flex items-center gap-1.5 rounded-md border border-accent-border bg-accent-soft px-2.5 py-1 font-mono text-sm text-accent"
            >
              {tag}
              <button
                type="button"
                aria-label={`Remove tag ${tag}`}
                className="rounded hover:bg-accent hover:text-white"
                onClick={() => onChange(value.filter((t) => t !== tag))}
              >
                <X className="h-3 w-3" strokeWidth={2} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <Input
        id={`${id}-input`}
        list={`${id}-options`}
        value={draft}
        placeholder="Type a tag..."
        aria-invalid={Boolean(shownError)}
        aria-describedby={[shownError ? `${id}-error` : null, hintId].filter(Boolean).join(" ") || undefined}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
        onBlur={commit}
      />
      <p id={hintId} className="mt-1.5 text-xs text-text-muted">
        Press Enter or comma to add
      </p>
      <datalist id={`${id}-options`}>
        {suggestions
          .filter((name) => !value.includes(name))
          .map((name) => (
            <option key={name} value={name} />
          ))}
      </datalist>
      {shownError && (
        <p id={`${id}-error`} className="mt-1.5 text-sm text-danger">
          {shownError}
        </p>
      )}
    </div>
  );
}
