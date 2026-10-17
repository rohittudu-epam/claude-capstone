import type { Metadata } from "next";

import { NoteView } from "@/components/notes/note-view";

export const metadata: Metadata = { title: "Edit note" };

export default async function NotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <NoteView id={id} />;
}
