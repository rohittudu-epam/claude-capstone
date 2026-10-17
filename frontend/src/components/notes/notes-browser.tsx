"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { TagFilter } from "@/components/notes/tag-filter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Badge, EmptyState, ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { useDebouncedValue } from "@/lib/hooks";
import type { NoteSummary, Page } from "@/lib/types";
import { formatDate } from "@/lib/utils";

type NoteRow = Pick<NoteSummary, "id" | "title" | "tags" | "updated_at">;

const PAGE_SIZE = 20;
const SEARCH_DELAY_MS = 300;

export function NotesBrowser() {
  const [text, setText] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [offset, setOffset] = useState(0);
  const search = useDebouncedValue(text.trim(), SEARCH_DELAY_MS);
  const searching = search.length > 0;

  const tags = useQuery({ queryKey: ["tags"], queryFn: api.listTags });
  const notes = useQuery({
    queryKey: ["notes", { search, tags: selectedTags, offset }],
    queryFn: async (): Promise<Page<NoteRow>> => {
      const params = { tags: selectedTags, limit: PAGE_SIZE, offset };
      return searching ? api.searchNotes(search, params) : api.listNotes(params);
    },
    placeholderData: keepPreviousData,
  });

  function changeText(value: string) {
    setText(value);
    setOffset(0);
  }

  function changeTags(next: string[]) {
    setSelectedTags(next);
    setOffset(0);
  }

  const total = notes.data?.total ?? 0;
  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + PAGE_SIZE, total);
  const filtered = searching || selectedTags.length > 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Notes</h1>
        <Button asChild>
          <Link href="/notes/new">New note</Link>
        </Button>
      </div>

      <Input
        type="search"
        aria-label="Search notes"
        placeholder="Search titles and text…"
        value={text}
        onChange={(event) => changeText(event.target.value)}
      />
      {tags.data ? <TagFilter tags={tags.data} selected={selectedTags} onChange={changeTags} /> : null}

      {notes.isPending ? <Loading>Loading notes…</Loading> : null}
      {notes.isError ? <ErrorNotice message={describeError(notes.error)} onRetry={() => notes.refetch()} /> : null}

      {notes.data ? (
        notes.data.items.length === 0 ? (
          filtered ? (
            <EmptyState title="No notes match your search">Try different words or clear the filters.</EmptyState>
          ) : (
            <EmptyState title="You have no notes yet">
              <Link className="text-brand underline" href="/notes/new">
                Write your first note
              </Link>
            </EmptyState>
          )
        ) : (
          <>
            <ul aria-label="Notes" className="divide-y divide-border rounded-md border border-border bg-surface">
              {notes.data.items.map((note) => (
                <li key={note.id} className="flex flex-wrap items-center gap-3 p-4">
                  <Link href={`/notes/${note.id}`} className="font-medium text-brand hover:underline">
                    {note.title}
                  </Link>
                  <span className="flex gap-1">
                    {note.tags.map((tag) => (
                      <Badge key={tag}>{tag}</Badge>
                    ))}
                  </span>
                  <time dateTime={note.updated_at} className="ml-auto text-xs text-ink-soft">
                    Updated {formatDate(note.updated_at)}
                  </time>
                </li>
              ))}
            </ul>
            <nav aria-label="Pagination" className="flex items-center justify-between text-sm">
              <p aria-live="polite">
                Showing {first}–{last} of {total}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </Button>
                <Button variant="secondary" size="sm" disabled={last >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                  Next
                </Button>
              </div>
            </nav>
          </>
        )
      ) : null}
    </div>
  );
}
