"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Sidebar, SidebarHeader, SidebarSection, SidebarSectionLabel, SidebarHintBar } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/button";
import { KeyCap } from "@/components/ui/key-cap";
import { Badge } from "@/components/ui/badge";
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
  const total = suggestions.data?.total ?? 0;

  return (
    <>
      {/* Sidebar */}
      <Sidebar>
        <SidebarHeader>
          <h2 className="font-mono text-sm font-semibold text-text-primary">Link Suggestions</h2>
        </SidebarHeader>

        <SidebarSection>
          <SidebarSectionLabel count={total}>Pending</SidebarSectionLabel>
          <div className="space-y-2 text-sm">
            <p className="text-text-secondary">
              Notes that share keywords. Nothing is linked until you decide.
            </p>
          </div>
        </SidebarSection>

        <div className="flex-1" />
        <SidebarHintBar>
          <span>
            <KeyCap>↑</KeyCap>
            <KeyCap>↓</KeyCap> navigate
          </span>
          <span>
            <KeyCap>A</KeyCap> accept
          </span>
          <span>
            <KeyCap>R</KeyCap> reject
          </span>
        </SidebarHintBar>
      </Sidebar>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <PageHeader
          title={`Link suggestions (${total})`}
          badge={`${total} pending`}
          description="Review and approve suggested links between related notes"
        />

        <div className="flex-1 overflow-y-auto p-6">
          <div aria-live="polite" className="mb-4">
            {notice && (
              <div role="status" className="rounded-lg border border-success/30 bg-success/10 p-3 text-sm text-success">
                {notice}
              </div>
            )}
          </div>

          {suggestions.isPending && (
            <div className="flex h-64 items-center justify-center">
              <Loading>Loading suggestions…</Loading>
            </div>
          )}

          {suggestions.isError && (
            <div className="flex h-64 items-center justify-center">
              <ErrorNotice message={describeError(suggestions.error)} onRetry={() => suggestions.refetch()} />
            </div>
          )}

          {suggestions.data && items.length === 0 && (
            <div className="flex h-64 items-center justify-center">
              <EmptyState title="No suggestions to review">
                Suggestions appear after you save notes that mention the same things.
              </EmptyState>
            </div>
          )}

          <div role="list" aria-label="Link suggestions" className="space-y-4">
            {items.map((suggestion) => {
              const { source_note: a, target_note: b } = suggestion;
              const working = busy[suggestion.id];
              const matchPercent = Math.round(suggestion.similarity_score * 100);

              return (
                <article
                  key={suggestion.id}
                  role="listitem"
                  className="rounded-xl border border-border-subtle bg-bg-surface p-6 transition-all duration-150"
                >
                  {/* Note Cards Side by Side */}
                  <div className="flex items-center gap-4">
                    {/* Source Note */}
                    <Link
                      href={`/notes/${a.id}`}
                      className="flex-1 rounded-lg border border-border-strong bg-bg-elevated p-4 transition-all duration-150 hover:border-accent hover:shadow-md"
                    >
                      <h3 className="font-mono text-base font-semibold text-text-primary">{a.title}</h3>
                    </Link>

                    {/* Connection Indicator */}
                    <div className="flex flex-col items-center gap-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-dashed border-accent-border bg-accent-soft">
                        <ArrowRight className="h-5 w-5 text-accent" strokeWidth={2} />
                      </div>
                      <Badge variant="accent" className="text-xs font-semibold">
                        {matchPercent}% match
                      </Badge>
                    </div>

                    {/* Target Note */}
                    <Link
                      href={`/notes/${b.id}`}
                      className="flex-1 rounded-lg border border-border-strong bg-bg-elevated p-4 transition-all duration-150 hover:border-accent hover:shadow-md"
                    >
                      <h3 className="font-mono text-base font-semibold text-text-primary">{b.title}</h3>
                    </Link>
                  </div>

                  {/* Explanation */}
                  <p className="mt-4 text-sm text-text-secondary">{suggestion.explanation}</p>

                  {/* Error Display */}
                  {rowErrors[suggestion.id] && (
                    <p role="alert" className="mt-3 rounded-lg border border-danger/30 bg-danger/10 p-2 text-sm text-danger">
                      {rowErrors[suggestion.id]}
                    </p>
                  )}

                  {/* Actions */}
                  <div className="mt-4 flex gap-3">
                    <Button
                      size="md"
                      loading={working === "accept"}
                      disabled={Boolean(working)}
                      aria-label={`Accept link between ${a.title} and ${b.title}`}
                      onClick={() => act(suggestion, "accept")}
                      className="flex-1"
                    >
                      <Check className="h-4 w-4" strokeWidth={2} />
                      {working === "accept" ? "Linking…" : "Accept"}
                    </Button>
                    <Button
                      size="md"
                      variant="ghost"
                      loading={working === "reject"}
                      disabled={Boolean(working)}
                      aria-label={`Reject link between ${a.title} and ${b.title}`}
                      onClick={() => act(suggestion, "reject")}
                      className="flex-1"
                    >
                      <X className="h-4 w-4" strokeWidth={2} />
                      {working === "reject" ? "Dismissing…" : "Reject"}
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
