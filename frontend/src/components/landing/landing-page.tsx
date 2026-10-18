"use client";

import { Check, FileText, GitFork, Network, Keyboard, Search, Zap } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/ui/logo";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";

export function LandingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const features = [
    {
      icon: FileText,
      title: "Markdown Editor",
      description: "Write notes in Markdown with live preview, syntax highlighting, and tag support.",
    },
    {
      icon: Search,
      title: "Fast Search & Tags",
      description: "Find any note instantly with full-text search and flexible tag filtering.",
    },
    {
      icon: GitFork,
      title: "Smart Link Suggestions",
      description: "Get AI-powered suggestions for connecting related notes based on shared keywords.",
    },
    {
      icon: Network,
      title: "Interactive Knowledge Graph",
      description: "Visualize connections between notes in a dynamic, explorable graph.",
    },
    {
      icon: Check,
      title: "You Approve Every Link",
      description: "Nothing is linked until you decide. Accept suggestions you trust, reject the rest.",
    },
    {
      icon: Keyboard,
      title: "Keyboard-First Writing",
      description: "Optimized for keyboard navigation with shortcuts throughout the interface.",
    },
  ];

  const faqs = [
    {
      question: "How does LinkNote suggest connections?",
      answer:
        "LinkNote analyzes the content of your notes and identifies shared keywords. When two notes mention similar topics, you'll see a suggestion to link them. You review each suggestion and decide whether to accept or reject it.",
    },
    {
      question: "Is my data private?",
      answer:
        "Yes. Your notes are stored securely and only accessible to you. We don't sell your data or use it for advertising. All processing happens on our servers to generate link suggestions, but your content remains private.",
    },
    {
      question: "Can I export my notes?",
      answer:
        "Yes. All notes are stored as Markdown, a plain-text format that works anywhere. You can export your notes at any time and use them with other Markdown tools.",
    },
    {
      question: "What happens to rejected suggestions?",
      answer:
        "Rejected suggestions are dismissed permanently. If the notes change and become even more related, a new suggestion may appear, but you won't see the same suggestion twice.",
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-bg-app">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-border-subtle bg-bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Logo className="h-6 w-6 text-accent" />
            <span className="text-lg font-semibold text-text-primary">LinkNote</span>
          </div>

          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/register">Get started</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-border-subtle">
        {/* Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-b from-accent/20 via-accent/5 to-bg-app" />

        <div className="relative mx-auto max-w-7xl px-6 py-24 text-center">
          <h1 className="text-5xl font-bold leading-tight text-text-primary sm:text-6xl">
            Your notes,{" "}
            <span className="bg-gradient-to-r from-accent to-accent-hover bg-clip-text text-transparent">
              connected
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-text-secondary">
            Turn your Markdown notes into a knowledge graph. Smart link suggestions you approve, keyboard-first writing,
            and an interactive graph that reveals how your ideas connect.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/register">Get started free</Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link href="#features">See how it works</Link>
            </Button>
          </div>

          {/* App Window Mockup */}
          <div className="mt-16">
            <div className="mx-auto max-w-5xl rounded-2xl border border-border-subtle bg-bg-surface shadow-2xl">
              <div className="aspect-video overflow-hidden rounded-2xl border-b border-border-subtle bg-bg-app p-8">
                <div className="flex h-full items-center justify-center text-text-muted">
                  <div className="text-center">
                    <Network className="mx-auto h-16 w-16 text-accent opacity-50" strokeWidth={1.5} />
                    <p className="mt-4 text-sm">Interactive graph preview</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Strip */}
      <section className="border-b border-border-subtle bg-bg-surface py-8">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-text-secondary">
            <span className="flex items-center gap-2">
              <Check className="h-4 w-4 text-success" strokeWidth={2} />
              Markdown-first
            </span>
            <span className="flex items-center gap-2">
              <Check className="h-4 w-4 text-success" strokeWidth={2} />
              You approve every link
            </span>
            <span className="flex items-center gap-2">
              <Check className="h-4 w-4 text-success" strokeWidth={2} />
              Keyboard-friendly
            </span>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="border-b border-border-subtle py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-text-primary">Everything you need</h2>
            <p className="mt-4 text-lg text-text-secondary">Powerful features for building your knowledge graph</p>
          </div>

          <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border border-border-subtle bg-bg-surface p-6 transition-all duration-150 hover:border-border-strong hover:shadow-md"
              >
                <feature.icon className="h-8 w-8 text-accent" strokeWidth={1.5} />
                <h3 className="mt-4 text-lg font-semibold text-text-primary">{feature.title}</h3>
                <p className="mt-2 text-sm text-text-secondary">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-b border-border-subtle bg-bg-surface py-24">
        <div className="mx-auto max-w-7xl px-6">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-text-primary">How it works</h2>
            <p className="mt-4 text-lg text-text-secondary">Three simple steps to a connected knowledge base</p>
          </div>

          <div className="mt-16 grid gap-12 lg:grid-cols-3">
            {[
              {
                step: "1",
                title: "Write",
                description: "Create Markdown notes with tags. Write freely about any topic.",
              },
              {
                step: "2",
                title: "Review",
                description: "Get smart suggestions for linking related notes. Accept what makes sense, reject the rest.",
              },
              {
                step: "3",
                title: "Explore",
                description: "Visualize your knowledge graph. Discover connections and patterns in your thinking.",
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border-2 border-accent bg-accent-soft font-mono text-lg font-semibold text-accent">
                  {item.step}
                </div>
                <h3 className="mt-4 text-xl font-semibold text-text-primary">{item.title}</h3>
                <p className="mt-2 text-text-secondary">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="border-b border-border-subtle py-24">
        <div className="mx-auto max-w-3xl px-6">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-text-primary">Frequently asked questions</h2>
          </div>

          <div className="mt-12 space-y-4">
            {faqs.map((faq, index) => (
              <div key={index} className="rounded-xl border border-border-subtle bg-bg-surface">
                <button
                  onClick={() => setOpenFaq(openFaq === index ? null : index)}
                  className="flex w-full items-center justify-between p-6 text-left"
                >
                  <span className="font-semibold text-text-primary">{faq.question}</span>
                  <span className="text-accent">{openFaq === index ? "−" : "+"}</span>
                </button>
                {openFaq === index && (
                  <div className="border-t border-border-subtle px-6 py-4">
                    <p className="text-sm text-text-secondary">{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative overflow-hidden border-b border-border-subtle">
        <div className="absolute inset-0 bg-gradient-to-r from-accent/20 to-accent-hover/20" />
        <div className="relative mx-auto max-w-4xl px-6 py-24 text-center">
          <h2 className="text-3xl font-bold text-text-primary">Start building your knowledge graph</h2>
          <p className="mt-4 text-lg text-text-secondary">Free to start. No credit card required.</p>
          <div className="mt-8">
            <Button size="lg" asChild>
              <Link href="/register">Get started free</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-bg-surface py-12">
        <div className="mx-auto max-w-7xl px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-3">
              <Logo className="h-6 w-6 text-accent" />
              <span className="text-sm text-text-secondary">
                © {new Date().getFullYear()} LinkNote. Turn your notes into a knowledge graph.
              </span>
            </div>
            <div className="flex gap-6 text-sm text-text-secondary">
              <Link href="/login" className="hover:text-text-primary">
                Sign in
              </Link>
              <Link href="/register" className="hover:text-text-primary">
                Get started
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
