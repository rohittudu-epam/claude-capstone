import type { Metadata } from "next";

import { NotesBrowser } from "@/components/notes/notes-browser";

export const metadata: Metadata = { title: "Notes" };

export default function NotesPage() {
  return <NotesBrowser />;
}
