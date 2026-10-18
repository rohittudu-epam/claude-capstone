"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Markdown } from "@/components/notes/markdown";
import { TagInput } from "@/components/notes/tag-input";
import { Button } from "@/components/ui/button";
import { describeError } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { ApiError, api } from "@/lib/api";
import type { Note } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

const MAX_TITLE_LENGTH = 500;
const MAX_BODY_BYTES = 512 * 1024;

type Errors = { title?: string; body?: string; tags?: string };

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
  const submitting = useRef(false); // synchronous guard: state updates are too late to stop a double click
  const titleRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  useEffect(() => {
    if (!note) titleRef.current?.focus();
  }, [note]);

  const dirty = note
    ? title !== note.title || body !== note.body || tags.join("\n") !== note.tags.join("\n")
    : Boolean(title || body || tags.length);

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

  const existingTags = useQuery({ queryKey: ["tags"], queryFn: api.listTags });

  function edited<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setSaved(false);
    };
  }

  function validate(): Errors {
    const next: Errors = {};
    if (!title.trim()) next.title = "Give the note a title.";
    else if (title.trim().length > MAX_TITLE_LENGTH) next.title = `The title can be at most ${MAX_TITLE_LENGTH} characters.`;
    if (new TextEncoder().encode(body).length > MAX_BODY_BYTES) {
      next.body = `The note is too long (limit ${MAX_BODY_BYTES / 1024} KiB).`;
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
        return; // stay locked while navigating away, so a late second click can't create a duplicate
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

  return (
    <form onSubmit={onSubmit} onKeyDown={onKeyDown} noValidate className="space-y-4" aria-label={note ? "Edit note" : "New note"}>
      {formError ? (
        <p role="alert" className="rounded-md border border-danger bg-surface p-3 text-sm text-danger">
          {formError}
        </p>
      ) : null}

      <Field id="title" label="Title" error={errors.title}>
        {(props) => (
          <Input {...props} ref={titleRef} value={title} onChange={(e) => edited(setTitle)(e.target.value)} maxLength={MAX_TITLE_LENGTH + 50} />
        )}
      </Field>

      <TagInput
        value={tags}
        onChange={edited(setTags)}
        suggestions={(existingTags.data ?? []).map((t) => t.name)}
        error={errors.tags}
      />

      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-sm font-medium" id="body-label">
            Note (Markdown)
          </span>
          <div role="group" aria-label="Editor mode" className="flex rounded-md border border-border">
            {(["write", "preview"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={mode === value}
                onClick={() => setMode(value)}
                className={cn("px-3 py-1 text-sm capitalize", mode === value ? "bg-brand text-brand-foreground" : "bg-surface")}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
        {mode === "write" ? (
          <Field id="body" label="Markdown text" error={errors.body}>
            {(props) => (
              <Textarea {...props} value={body} onChange={(e) => edited(setBody)(e.target.value)} />
            )}
          </Field>
        ) : (
          <div aria-label="Preview" className="min-h-64 rounded-md border border-border bg-surface p-4">
            {body.trim() ? <Markdown>{body}</Markdown> : <p className="text-ink-soft">Nothing to preview yet.</p>}
          </div>
        )}
      </div>

      {note ? (
        <p className="text-xs text-ink-soft">
          Created <time dateTime={note.created_at}>{formatDate(note.created_at)}</time> · Updated{" "}
          <time dateTime={note.updated_at}>{formatDate(note.updated_at)}</time>
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : note ? "Save changes" : "Create note"}
        </Button>
        <Button variant="secondary" disabled={saving} onClick={cancel}>
          Cancel
        </Button>
        {saved ? <span role="status">Saved.</span> : null}
        {note && !confirmingDelete ? (
          <Button variant="secondary" className="ml-auto" onClick={() => setConfirmingDelete(true)}>
            Delete
          </Button>
        ) : null}
        {note && confirmingDelete ? (
          <div role="alertdialog" aria-label="Confirm delete" className="ml-auto flex items-center gap-2">
            <span className="text-sm">Delete this note? This cannot be undone.</span>
            <Button variant="danger" size="sm" disabled={deleting} onClick={onDelete}>
              {deleting ? "Deleting…" : "Yes, delete"}
            </Button>
            <Button variant="secondary" size="sm" disabled={deleting} onClick={() => setConfirmingDelete(false)}>
              Cancel
            </Button>
          </div>
        ) : null}
      </div>
    </form>
  );
}
