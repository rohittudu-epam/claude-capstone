"use client";

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
  return (
    <div>
      <Label htmlFor={`${id}-input`}>Tags</Label>
      {value.length > 0 ? (
        <ul aria-label="Selected tags" className="mb-2 flex flex-wrap gap-2">
          {value.map((tag) => (
            <li key={tag} className="flex items-center gap-1 rounded-full bg-muted py-0.5 pl-3 pr-1 text-sm">
              {tag}
              <button
                type="button"
                aria-label={`Remove tag ${tag}`}
                className="rounded-full px-2 hover:bg-border"
                onClick={() => onChange(value.filter((t) => t !== tag))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <Input
        id={`${id}-input`}
        list={`${id}-options`}
        value={draft}
        placeholder="Type a tag, press Enter"
        aria-invalid={Boolean(shownError)}
        aria-describedby={shownError ? `${id}-error` : undefined}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
        onBlur={commit}
      />
      <datalist id={`${id}-options`}>
        {suggestions
          .filter((name) => !value.includes(name))
          .map((name) => (
            <option key={name} value={name} />
          ))}
      </datalist>
      {shownError ? (
        <p id={`${id}-error`} className="mt-1 text-sm text-danger">
          {shownError}
        </p>
      ) : null}
    </div>
  );
}
