import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Providers } from "@/app/providers";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: { default: "LinkNote", template: "%s · LinkNote" },
  description: "Turn your Markdown notes into a knowledge graph. Smart link suggestions you approve, keyboard-first writing.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    type: "website",
    title: "LinkNote",
    description: "Turn your Markdown notes into a knowledge graph",
    siteName: "LinkNote",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-bg-surface focus:p-3 focus:text-text-primary"
        >
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
