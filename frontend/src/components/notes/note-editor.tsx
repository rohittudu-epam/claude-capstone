"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Markdown } from "@/components/notes/markdown";
import { TagInput } from "@/components/notes/tag-input";
import { Button } from "@/components/ui/button";
import { describeError } from "@/components/ui/feedback";
import { Input, Label, Textarea } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { ApiError, api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const MAX_TITLE_LENGTH = 500;
const MAX_BODY_BYTES = 512 * 1024;

type Errors = { title?: string; body?: string; tags?: string };

function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function NoteEditor({ note }: { note?: Note }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(note?.title ?? "");
  const [body, setBody] = useState(note?.body ?? "");
  const [tags, setTags] = useState<string[]>(note?.tags ?? []);
  const [mode, setMode] = useState<"write" | "preview">("write");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [titleTouched, setTitleTouched] = useState(false);
  const submitting = useRef(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  useEffect(() => {
    if (!note) titleRef.current?.focus();
  }, [note]);

  const dirty = note
    ? title !== note.title || body !== note.body || tags.join("\n") !== note.tags.join("\n")
    : Boolean(title || body || tags.length);

  const wordCount = countWords(body);

  function cancel() {
    if (dirty && !window.confirm("Discard your changes?")) return;
    router.push("/notes");
  }

  function onKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      event.currentTarget.requestSubmit();
    }
  }

  // Handle tab switching with arrow keys
  function onTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, tabValue: "write" | "preview") {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      setMode(tabValue === "write" ? "preview" : "write");
      const next = event.currentTarget.nextElementSibling as HTMLButtonElement | null;
      next?.focus();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      setMode(tabValue === "write" ? "preview" : "write");
      const prev = event.currentTarget.previousElementSibling as HTMLButtonElement | null;
      prev?.focus();
    }
  }

  const existingTags = useQuery({ queryKey: ["tags"], queryFn: api.listTags });

  function edited<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setSaved(false);
    };
  }

  function validate(): Errors {
    const next: Errors = {};
    if (!title.trim()) next.title = "Give your note a title";
    else if (title.trim().length > MAX_TITLE_LENGTH) next.title = `The title can be at most ${MAX_TITLE_LENGTH} characters`;
    if (new TextEncoder().encode(body).length > MAX_BODY_BYTES) {
      next.body = `The note is too long (limit ${MAX_BODY_BYTES / 1024} KiB)`;
    }
    return next;
  }

  function refreshCaches() {
    for (const key of ["notes", "tags", "graph", "suggestions", "links"]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;

    setTitleTouched(true);
    const next = validate();
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length > 0) return;

    submitting.current = true;
    setSaving(true);
    try {
      const payload = { title: title.trim(), body, tags };
      const result = note ? await api.updateNote(note.id, payload) : await api.createNote(payload);
      queryClient.setQueryData(["note", result.id], result);
      refreshCaches();
      if (note) {
        setSaved(true);
        toast.success("Note updated");
      } else {
        toast.success("Note created");
        router.push("/notes");
        return;
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 400 && error.fieldErrors.length > 0) {
        const mapped: Errors = {};
        for (const { field, message } of error.fieldErrors) {
          if (field === "title" || field === "body") mapped[field] = message;
          else if (field.startsWith("tags")) mapped.tags = message;
        }
        setErrors(mapped);
        if (Object.keys(mapped).length === 0) setFormError(describeError(error));
      } else {
        setFormError(describeError(error));
      }
    }
    submitting.current = false;
    setSaving(false);
  }

  async function onDelete() {
    if (!note) return;
    setDeleting(true);
    try {
      await api.deleteNote(note.id);
      queryClient.removeQueries({ queryKey: ["note", note.id] });
      refreshCaches();
      router.push("/notes");
    } catch (error) {
      setFormError(describeError(error));
      setConfirmingDelete(false);
      setDeleting(false);
    }
  }

  const titleError = titleTouched ? errors.title : undefined;
  const canSubmit = !saving && title.trim().length > 0;

  return (
    <form onSubmit={onSubmit} onKeyDown={onKeyDown} noValidate className="space-y-5" aria-label={note ? "Edit note" : "New note"}>
      {formError && (
        <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {formError}
        </div>
      )}

      {/* Title Field */}
      <div>
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          ref={titleRef}
          value={title}
          onChange={(e) => {
            edited(setTitle)(e.target.value);
            if (titleTouched) {
              const next = validate();
              setErrors((prev) => ({ ...prev, title: next.title }));
            }
          }}
          onBlur={() => {
            setTitleTouched(true);
            const next = validate();
            setErrors((prev) => ({ ...prev, title: next.title }));
          }}
          maxLength={MAX_TITLE_LENGTH + 50}
          placeholder="Untitled note"
          aria-invalid={Boolean(titleError)}
          aria-describedby={titleError ? "title-error" : undefined}
          className="text-lg"
        />
        {titleError && (
          <p id="title-error" className="mt-1.5 text-sm text-danger">
            {titleError}
          </p>
        )}
      </div>

      {/* Tags Field */}
      <TagInput
        value={tags}
        onChange={edited(setTags)}
        suggestions={(existingTags.data ?? []).map((t) => t.name)}
        error={errors.tags}
      />

      {/* Editor Section */}
      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <Label id="body-label">Note</Label>
          <div role="tablist" aria-label="Editor mode" className="flex rounded-lg border border-border-strong overflow-hidden">
            {(["write", "preview"] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={mode === value}
                aria-controls={`${value}-panel`}
                onClick={() => setMode(value)}
                onKeyDown={(e) => onTabKeyDown(e, value)}
                tabIndex={mode === value ? 0 : -1}
                className={cn(
                  "px-4 py-1.5 text-sm font-medium capitalize transition-all duration-150",
                  mode === value
                    ? "bg-accent-soft text-accent"
                    : "bg-bg-surface text-text-secondary hover:bg-bg-hover hover:text-text-primary",
                )}
              >
                {value}
              </button>
            ))}
          </div>
        </div>

        {mode === "write" ? (
          <div id="write-panel" role="tabpanel" aria-labelledby="body-label">
            <Textarea
              id="body"
              value={body}
              onChange={(e) => edited(setBody)(e.target.value)}
              placeholder="Write in Markdown..."
              aria-label="Note content, Markdown"
              aria-invalid={Boolean(errors.body)}
              aria-describedby={errors.body ? "body-error" : "word-count"}
            />
            <div className="mt-1.5 flex items-center justify-between text-xs text-text-muted">
              <span id="word-count">{wordCount} {wordCount === 1 ? "word" : "words"}</span>
            </div>
            {errors.body && (
              <p id="body-error" className="mt-1.5 text-sm text-danger">
                {errors.body}
              </p>
            )}
          </div>
        ) : (
          <div
            id="preview-panel"
            role="tabpanel"
            aria-labelledby="body-label"
            className="min-h-[280px] rounded-lg border border-border-subtle bg-bg-elevated p-4"
          >
            {body.trim() ? <Markdown>{body}</Markdown> : <p className="text-text-muted">Nothing to preview yet</p>}
          </div>
        )}
      </div>

      {note && (
        <p className="text-xs text-text-secondary">
          Created <time dateTime={note.created_at}>{formatDate(note.created_at)}</time> · Updated{" "}
          <time dateTime={note.updated_at}>{formatDate(note.updated_at)}</time>
        </p>
      )}

      {/* Actions - Sticky on mobile */}
      <div className="fixed bottom-0 left-0 right-0 z-20 border-t border-border-subtle bg-bg-surface p-4 shadow-lg sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={!canSubmit} loading={saving} className="flex-1 sm:flex-initial">
            {note ? "Save changes" : "Create note"}
          </Button>
          <Button variant="ghost" disabled={saving} onClick={cancel} className="flex-1 sm:flex-initial">
            Cancel
          </Button>
          {saved && <span role="status" className="hidden text-sm text-success sm:inline">Saved</span>}
          {note && !confirmingDelete && (
            <Button variant="secondary" className="ml-auto hidden sm:inline-flex" onClick={() => setConfirmingDelete(true)}>
              Delete
            </Button>
          )}
          {note && confirmingDelete && (
            <div role="alertdialog" aria-label="Confirm delete" className="ml-auto flex flex-wrap items-center gap-2">
              <span className="text-sm text-text-secondary">Delete this note? This cannot be undone.</span>
              <Button variant="danger" size="sm" disabled={deleting} onClick={onDelete}>
                {deleting ? "Deleting…" : "Yes, delete"}
              </Button>
              <Button variant="secondary" size="sm" disabled={deleting} onClick={() => setConfirmingDelete(false)}>
                Cancel
              </Button>
            </div>
          )}
        </div>
        <p className="mt-2 text-xs text-text-muted sm:mt-3">
          <kbd className="key-cap">Ctrl</kbd>+<kbd className="key-cap">Enter</kbd> to save
        </p>
      </div>
    </form>
  );
}
