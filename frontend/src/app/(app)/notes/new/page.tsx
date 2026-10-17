import type { Metadata } from "next";

import { NoteEditor } from "@/components/notes/note-editor";

export const metadata: Metadata = { title: "New note" };

export default function NewNotePage() {
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">New note</h1>
      <NoteEditor />
    </div>
  );
}
