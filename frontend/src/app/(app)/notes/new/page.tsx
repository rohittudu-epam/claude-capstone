import type { Metadata } from "next";

import { NoteEditor } from "@/components/notes/note-editor";

export const metadata: Metadata = { title: "New note" };

export default function NewNotePage() {
  return (
    <div className="mx-auto w-full max-w-[1500px] px-4 pb-10 pt-5 sm:px-6 sm:pt-6 lg:px-8">
      <header className="mb-6 border-b border-border-subtle pb-5">
        <p className="section-label mb-2">Workspace / Notes</p>
        <h1 className="font-mono text-2xl font-semibold text-text-primary sm:text-3xl">New note</h1>
        <p className="mt-1 text-sm text-text-secondary">Capture an idea in Markdown.</p>
      </header>
      <NoteEditor />
    </div>
  );
}
