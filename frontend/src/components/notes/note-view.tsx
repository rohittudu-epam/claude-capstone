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
    <section aria-labelledby="linked-heading" className="mt-8">
      <h2 id="linked-heading" className="mb-2 text-lg font-semibold">
        Linked notes
      </h2>
      {items.length === 0 ? (
        <p className="text-sm text-ink-soft">
          No linked notes yet. <Link className="text-brand underline" href="/suggestions">Review suggestions</Link> to connect
          related notes.
        </p>
      ) : (
        <ul className="space-y-1">
          {items.map((link) => {
            const other = link.source_note.id === noteId ? link.target_note : link.source_note;
            return (
              <li key={link.id}>
                <Link className="text-brand hover:underline" href={`/notes/${other.id}`}>
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
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Edit note</h1>
      <NoteEditor key={note.data.id} note={note.data} />
      <LinkedNotes noteId={note.data.id} />
    </div>
  );
}
