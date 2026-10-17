import type { Metadata } from "next";

import { SuggestionsList } from "@/components/suggestions/suggestions-list";

export const metadata: Metadata = { title: "Suggestions" };

export default function SuggestionsPage() {
  return <SuggestionsList />;
}
