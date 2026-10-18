"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Sidebar, SidebarHeader, SidebarSection, SidebarSectionLabel, SidebarRow, SidebarHintBar } from "@/components/layout/sidebar";
import { TagFilter } from "@/components/notes/tag-filter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { KeyCap } from "@/components/ui/key-cap";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
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
    <>
      {/* Sidebar */}
      <Sidebar>
        <SidebarHeader>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" strokeWidth={1.5} />
            <Input
              type="search"
              aria-label="Search notes"
              placeholder="Search…"
              value={text}
              onChange={(event) => changeText(event.target.value)}
              className="h-9 pl-9 pr-8"
            />
            <KeyCap className="absolute right-3 top-1/2 -translate-y-1/2">/</KeyCap>
          </div>
        </SidebarHeader>

        {tags.data && tags.data.length > 0 && (
          <SidebarSection>
            <TagFilter tags={tags.data} selected={selectedTags} onChange={changeTags} />
          </SidebarSection>
        )}

        <SidebarSection>
          <SidebarSectionLabel count={total}>Notes</SidebarSectionLabel>
          <div className="space-y-1">
            {notes.isPending && <Loading>Loading notes…</Loading>}
            {notes.isError && <ErrorNotice message={describeError(notes.error)} onRetry={() => notes.refetch()} />}
            {notes.data?.items.slice(0, 20).map((note) => (
              <Link key={note.id} href={`/notes/${note.id}`}>
                <SidebarRow
                  title={note.title}
                  meta={`${note.tags.length} ${note.tags.length === 1 ? "tag" : "tags"}`}
                  count={0}
                />
              </Link>
            ))}
          </div>
        </SidebarSection>

        <div className="flex-1" />
        <SidebarHintBar>
          <span>
            <KeyCap>↑</KeyCap>
            <KeyCap>↓</KeyCap> navigate
          </span>
          <span>
            <KeyCap>Enter</KeyCap> open
          </span>
        </SidebarHintBar>
      </Sidebar>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <PageHeader
          title="Notes"
          badge="All notes"
          description="Your Markdown notes with link suggestions"
          actions={
            <Button asChild>
              <Link href="/notes/new">+ New note</Link>
            </Button>
          }
        />

        <div className="flex-1 overflow-y-auto p-6">
          {notes.data ? (
            notes.data.items.length === 0 ? (
              filtered ? (
                <EmptyState title="No notes match your search">Try different words or clear the filters.</EmptyState>
              ) : (
                <EmptyState title="You have no notes yet">
                  <Button asChild className="mt-4">
                    <Link href="/notes/new">Create your first note</Link>
                  </Button>
                </EmptyState>
              )
            ) : (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  {notes.data.items.map((note) => (
                    <Link
                      key={note.id}
                      href={`/notes/${note.id}`}
                      className="group rounded-xl border border-border-subtle bg-bg-surface p-4 transition-all duration-150 hover:border-border-strong hover:shadow-md"
                    >
                      <h3 className="font-mono text-base font-semibold text-text-primary group-hover:text-accent transition-colors">
                        {note.title}
                      </h3>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {note.tags.map((tag) => (
                          <Badge key={tag} className="font-mono text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <time dateTime={note.updated_at} className="mt-3 block text-xs text-text-muted">
                        Updated {formatDate(note.updated_at)}
                      </time>
                    </Link>
                  ))}
                </div>

                {total > PAGE_SIZE && (
                  <nav aria-label="Pagination" className="flex items-center justify-between pt-4">
                    <p aria-live="polite" className="text-sm text-text-secondary">
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
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={last >= total}
                        onClick={() => setOffset(offset + PAGE_SIZE)}
                      >
                        Next
                      </Button>
                    </div>
                  </nav>
                )}
              </div>
            )
          ) : null}
        </div>
      </div>
    </>
  );
}
