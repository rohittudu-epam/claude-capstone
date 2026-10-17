"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState, ErrorNotice, Loading, describeError } from "@/components/ui/feedback";
import { ApiError, api } from "@/lib/api";
import type { Page, Suggestion } from "@/lib/types";

type Action = "accept" | "reject";

export function SuggestionsList() {
  const queryClient = useQueryClient();
  const suggestions = useQuery({ queryKey: ["suggestions"], queryFn: () => api.listSuggestions({ limit: 50 }) });
  const inFlight = useRef(new Set<string>()); // synchronous guard: state updates are too late to stop a double click
  const [busy, setBusy] = useState<Record<string, Action>>({});
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<string | null>(null);

  function removeFromList(id: string) {
    queryClient.setQueryData<Page<Suggestion>>(["suggestions"], (old) =>
      old ? { ...old, items: old.items.filter((s) => s.id !== id), total: Math.max(0, old.total - 1) } : old,
    );
  }

  async function act(suggestion: Suggestion, action: Action) {
    if (inFlight.current.has(suggestion.id)) return;
    inFlight.current.add(suggestion.id);
    setBusy((current) => ({ ...current, [suggestion.id]: action }));
    setRowErrors(({ [suggestion.id]: _cleared, ...rest }) => rest);
    setNotice(null);
    const pair = `“${suggestion.source_note.title}” and “${suggestion.target_note.title}”`;

    try {
      if (action === "accept") await api.acceptSuggestion(suggestion.id);
      else await api.rejectSuggestion(suggestion.id);
      removeFromList(suggestion.id);
      setNotice(action === "accept" ? `Linked ${pair}.` : `Dismissed the suggestion for ${pair}.`);
      if (action === "accept") {
        void queryClient.invalidateQueries({ queryKey: ["graph"] });
        void queryClient.invalidateQueries({ queryKey: ["links"] });
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        removeFromList(suggestion.id);
        setNotice("That suggestion was already handled, so it has been removed from the list.");
      } else if (error instanceof ApiError && error.status === 409) {
        removeFromList(suggestion.id);
        setNotice(
          "One of those notes changed, so the suggestion was out of date. It will return if the notes still match.",
        );
        void suggestions.refetch();
      } else {
        setRowErrors((current) => ({ ...current, [suggestion.id]: describeError(error) }));
      }
    } finally {
      inFlight.current.delete(suggestion.id);
      setBusy(({ [suggestion.id]: _done, ...rest }) => rest);
    }
  }

  const items = suggestions.data?.items ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">
        Link suggestions{suggestions.data ? ` (${suggestions.data.total})` : ""}
      </h1>
      <p className="text-sm text-ink-soft">
        Notes that share keywords. Accept to link them in your graph; reject to dismiss. Nothing is linked until you decide.
      </p>
      <div aria-live="polite">
        {notice ? <p role="status" className="rounded-md bg-surface p-3 text-sm">{notice}</p> : null}
      </div>

      {suggestions.isPending ? <Loading>Loading suggestions…</Loading> : null}
      {suggestions.isError ? (
        <ErrorNotice message={describeError(suggestions.error)} onRetry={() => suggestions.refetch()} />
      ) : null}
      {suggestions.data && items.length === 0 ? (
        <EmptyState title="No suggestions to review">
          Suggestions appear a moment after you save notes that mention the same things.
        </EmptyState>
      ) : null}

      <ul className="space-y-3">
        {items.map((suggestion) => {
          const { source_note: a, target_note: b } = suggestion;
          const working = busy[suggestion.id];
          return (
            <li key={suggestion.id} className="rounded-md border border-border bg-surface p-4">
              <p className="font-medium">
                <Link className="text-brand hover:underline" href={`/notes/${a.id}`}>
                  {a.title}
                </Link>
                <span aria-hidden="true"> ↔ </span>
                <span className="sr-only"> is related to </span>
                <Link className="text-brand hover:underline" href={`/notes/${b.id}`}>
                  {b.title}
                </Link>
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                {Math.round(suggestion.similarity_score * 100)}% match · {suggestion.explanation}
              </p>
              {rowErrors[suggestion.id] ? (
                <p role="alert" className="mt-2 text-sm text-danger">
                  {rowErrors[suggestion.id]}
                </p>
              ) : null}
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  disabled={Boolean(working)}
                  aria-label={`Accept link between ${a.title} and ${b.title}`}
                  onClick={() => act(suggestion, "accept")}
                >
                  {working === "accept" ? "Linking…" : "Accept"}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={Boolean(working)}
                  aria-label={`Reject link between ${a.title} and ${b.title}`}
                  onClick={() => act(suggestion, "reject")}
                >
                  {working === "reject" ? "Dismissing…" : "Reject"}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
