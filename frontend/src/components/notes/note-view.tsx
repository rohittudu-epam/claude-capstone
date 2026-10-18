"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { NoteEditor } from "@/components/notes/note-editor";
import { EmptyState, ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
import { ApiError, api } from "@/lib/api";

function LinkedNotes({ noteId }: { noteId: string }) {
  const links = useQuery({ queryKey: ["links", noteId], queryFn: () => api.listLinks({ noteId, limit: 100 }) });
  if (links.isPending || links.isError) return null;
  const items = links.data.items;

  return (
    <section aria-labelledby="linked-heading" className="mt-8 rounded-xl border border-border-subtle bg-bg-surface p-4 sm:p-5">
      <h2 id="linked-heading" className="mb-1 text-lg font-semibold">
        Linked notes
      </h2>
      <p className="mb-4 text-sm text-text-muted">Notes connected to this entry.</p>
      {items.length === 0 ? (
        <p className="text-sm text-text-secondary">
          No linked notes yet. <Link className="text-accent underline" href="/suggestions">Review suggestions</Link> to connect
          related notes.
        </p>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((link) => {
            const other = link.source_note.id === noteId ? link.target_note : link.source_note;
            return (
              <li key={link.id}>
                <Link className="block rounded-lg border border-border-subtle bg-bg-elevated px-3 py-2 text-sm text-accent transition-colors hover:border-accent-border hover:bg-bg-hover" href={`/notes/${other.id}`}>
                  {other.title}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function NoteView({ id }: { id: string }) {
  const note = useQuery({ queryKey: ["note", id], queryFn: () => api.getNote(id) });

  if (note.isPending) return <Loading>Loading note…</Loading>;
  if (note.error instanceof ApiError && (note.error.status === 404 || note.error.status === 400)) {
    return (
      <EmptyState title="Note not found">
        It may have been deleted.{" "}
        <Link className="text-brand underline" href="/notes">
          Back to your notes
        </Link>
      </EmptyState>
    );
  }
  if (note.isError) return <ErrorNotice message={describeError(note.error)} onRetry={() => note.refetch()} />;

  return (
    <div className="mx-auto w-full max-w-[1500px] px-4 pb-10 pt-5 sm:px-6 sm:pt-6 lg:px-8">
      <header className="mb-6 flex items-start justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <p className="section-label mb-2">Workspace / Notes</p>
          <h1 className="font-mono text-2xl font-semibold text-text-primary sm:text-3xl">Edit note</h1>
          <p className="mt-1 text-sm text-text-secondary">Update your note, tags, and Markdown content.</p>
        </div>
        <Link href="/notes" className="shrink-0 rounded-lg border border-border-strong px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary">
          Back to notes
        </Link>
      </header>
      <NoteEditor key={note.data.id} note={note.data} />
      <LinkedNotes noteId={note.data.id} />
    </div>
  );
}
