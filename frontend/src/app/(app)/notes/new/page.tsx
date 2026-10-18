import type { Metadata } from "next";

import { NoteEditor } from "@/components/notes/note-editor";

export const metadata: Metadata = { title: "New note" };

export default function NewNotePage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-24 pt-6 sm:px-6 sm:pt-8">
      <h1 className="mb-6 font-mono text-2xl font-semibold text-text-primary">New note</h1>
      <NoteEditor />
    </div>
  );
}
