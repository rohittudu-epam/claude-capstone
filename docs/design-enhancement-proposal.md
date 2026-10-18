You are working on LinkNote, a Markdown note-taking app with tags, a
"Suggestions" page (link suggestions between notes that share keywords) and a
"Graph" page (knowledge graph of notes and connections). It currently has a
plain dark UI. Your job is to (1) give the whole application a polished,
distinctive visual identity based on the design language described below and
(2) build a marketing landing page shown to visitors who are not logged in.

Start by exploring the codebase: stack, routing, auth/session handling, styling
approach (CSS modules, Tailwind, styled-components, etc.) and component
structure. Follow existing conventions. Do not change business logic, API
contracts or data models in this task; this is a visual and routing task.

## Design language (the north star for every screen)

The look is a precision "developer tool" aesthetic, inspired by a dark
security/graph dashboard: near-black surfaces, one hot orange-coral accent,
monospace identifiers, dense but calm layouts, and a glowing focal point in the
graph. It should feel technical, quiet and confident, not colorful or playful.

Principles:
- Restraint: the UI is almost entirely neutral grays on black. Orange is
  reserved for what matters: the primary action, the selected/focused item, the
  focal graph node and its edges, and key highlights. If everything glows,
  nothing does.
- Density with breathing room: small, crisp type (12 to 14px), tight rows, thin
  1px borders instead of heavy boxes or large shadows, and generous outer
  padding around the whole layout.
- Structure through hairlines: separate regions with subtle 1px borders in a
  slightly lighter neutral, not with different background blocks or thick
  dividers.
- Monospace for data, sans for chrome: anything that is an identifier (note
  titles inside lists and graph nodes, tags, counts, shortcuts, timestamps) uses
  a monospace face. Navigation, headings and body copy use a clean sans-serif.
- Focus and dimming: the selected item is lit (accent border, soft accent
  glow, brighter text) while everything out of scope is visibly dimmed
  (lower opacity), rather than hidden.
- Keyboard-first feel: show small keyboard hints (key caps) in the UI.

### Tokens (define as CSS variables or theme config; adjust values if needed
### to meet WCAG AA contrast)

Dark theme (default):
- --bg-app: #0b0b0c (page and canvas background, near-black)
- --bg-surface: #141415 (panels, sidebar)
- --bg-elevated: #1b1b1d (cards, inputs, menus)
- --bg-hover: #222224
- --border-subtle: #242426 (hairline dividers)
- --border-strong: #333336 (inputs, cards, selected-but-not-accent)
- --text-primary: #ececec
- --text-secondary: #9a9a9f
- --text-muted: #66666b
- --accent: #ff5a36 (orange-coral; the single brand color)
- --accent-hover: #ff6e4e
- --accent-soft: rgba(255, 90, 54, 0.12) (tinted backgrounds)
- --accent-border: rgba(255, 90, 54, 0.55)
- --accent-glow: 0 0 32px rgba(255, 90, 54, 0.35)
- --success: #3ddc84 (used sparingly, e.g. "linked" or "managed" style status text)
- --danger: #ff5a36 is shared with accent, so use a distinct tone for
  destructive actions: #ef4444
- --warning: #f5a524

Light theme (provide, but dark remains the default): off-white background
(#fafaf9), white surfaces, warm gray borders, the same orange accent
darkened slightly for contrast (#e8481f), near-black text.

Typography:
- UI/sans: Inter (fallback system-ui)
- Mono: JetBrains Mono or IBM Plex Mono (fallback ui-monospace)
- Scale: caption 11px, small 12px, body 13 to 14px, h3 15px, h2 18px, h1 22px,
  display 48 to 64px (landing only). Tight letter spacing on display sizes.
- Section labels: 11px, uppercase, letter-spaced (about 0.08em), muted color,
  with a count aligned right (for example "TAGS    8").

Shape and effects:
- Radii: 6px for small controls and chips, 8px for inputs and nodes, 12px for
  cards and panels, 14 to 16px for the large app-window frame.
- Borders: 1px everywhere. No heavy drop shadows inside the app; reserve a
  large soft shadow for floating surfaces (menus, modals, the landing mockup).
- Glow: use --accent-glow only on the focal graph node, primary button hover,
  and the focused search field.
- Subtle radial vignette: a faint radial gradient of the accent (very low
  opacity) behind the graph's focal node.
- Motion: 150 to 220ms ease-out; respect prefers-reduced-motion.
- Icons: thin 1.5px stroke line icons (Lucide or similar), 16px in dense UI.
  No emoji.

Signature components (build these as reusable primitives):
- Sidebar row: two-line item with a mono title and a muted meta line (for
  example "6 links"), count aligned right; the selected row gets a 1px strong
  border, a slightly lighter background, and an accent text color for its title.
- Section header: uppercase muted label plus right-aligned count.
- Filter chip: pill with 1px border; a dashed-border "+ Filter" chip to add a
  filter, and applied chips showing an "x" to remove.
- Status text: small colored word (success green or accent orange) used as a
  value, not as a filled badge.
- Key cap: tiny bordered rounded rectangle containing a key (/, F, Esc), used
  in hint bars.
- Hint pill: small bordered pill that explains the current view state (for
  example "dimmed = out of scope · 2 hops", with the key part in accent color).
- Header meta line: mono title followed by a small outlined type badge, then a
  one-line muted summary underneath, and quiet text-link actions aligned to the
  right of the header.
- Zoom control: small bordered capsule at the bottom-left of the canvas with
  "-  100%  +  Fit".
- Legend: small bordered capsule at the bottom-right of the canvas explaining
  line styles (solid accent = accepted link, dashed = suggested/pending).

## Part 1: Design system implementation (do this first)

Implement the tokens above as the single source of truth and refactor existing
hard-coded colors, spacing and font sizes to use them.

- Add the dark and light themes with a toggle (system preference by default,
  remembered choice, no flash of the wrong theme on load).
- Build or restyle primitives: Button (primary orange, secondary bordered,
  ghost, danger, loading state), Input/Textarea (dark elevated fill, 1px border,
  accent border and glow on focus), Tag chip (mono text, removable and
  selectable), Card, Badge, Segmented control, Modal, Dropdown menu, Toast,
  Skeleton, Empty state, Tooltip, Avatar (circle with orange-tinted initials),
  Key cap, Hint pill, Section header, Sidebar row.
- Brand: a simple logo mark of two or three linked nodes as inline SVG, using
  the accent color, plus a favicon and a social preview (Open Graph) image in
  the same style.

## Part 2: Restyle the authenticated app

Adopt a three-region application layout, collapsing gracefully on small screens:

- Left icon rail (about 56px): logo mark at the top; icon buttons for Notes,
  Suggestions and Graph with an accent-tinted active state and tooltips;
  settings and theme toggle plus the user avatar at the bottom. On mobile this
  becomes a bottom tab bar or a hamburger menu.
- Secondary sidebar (about 280px, context panel): a page title, a search field
  with an icon and a "/" key cap, filter chips (including the dashed "+ Filter"
  chip), then grouped sections with uppercase labels and counts. On the Notes
  page the sidebar lists tags and notes as sidebar rows. At the bottom, a hint
  bar with key caps (for example: arrows navigate, Enter open, F fit, Esc back).
  Collapsible, and a drawer on mobile.
- Main canvas: a header with a mono title, a small badge and a muted summary
  line, text-link actions on the right (for example "New note", "Export"), and
  the page content below.

Page-specific direction:
- Notes: the main area shows the selected note's detail or a dense list/card
  grid with mono titles, 1 to 2 line previews, tag chips, relative timestamps
  and a link count. The "+ New note" action is a primary orange button in the
  header.
- New/Edit note: an editor-focused layout. Large borderless title, tag input
  with chips, Write/Preview segmented control, Markdown toolbar with thin line
  icons, monospace editor, styled Markdown preview, word count, and a sticky
  footer with Save (primary) and Cancel.
- Suggestions: two notes shown side by side as bordered node-style cards
  (mono title, muted meta) with a thin orange connecting line and a link icon
  between them, shared keywords as chips, a slim match-score bar, and Accept
  (primary) and Reject (ghost) actions. Animate cards out when decided.
- Graph (the showpiece, replicate this closely):
  - Canvas on --bg-app with a faint dot grid and a soft orange radial glow
    behind the focal node.
  - Nodes are small rounded rectangles (8px radius) with a 1px border, two lines
    of text: the note title in mono and a muted meta line (for example
    "3 links" or its main tag). No filled circles.
  - The selected/focal note is rendered lit: orange fill or strong orange border,
    glow, brighter text. Notes directly connected to it are drawn at full
    opacity, notes farther away (beyond N hops, default 2) are dimmed to about
    25 to 35 percent opacity.
  - Edges are thin (1px) lines: solid accent for accepted/manual links, dashed
    for pending suggestions, very faint neutral for edges between dimmed nodes.
    Prefer clean straight or gently curved lines.
  - Layout: focal node centered, direct neighbors arranged on either side
    (a left and right column feel is fine), using a force or radial layout
    that keeps it tidy.
  - Controls: zoom/fit capsule bottom-left, legend capsule bottom-right, hint
    pill top-left showing the current depth ("dimmed = out of scope · 2 hops"),
    and a Graph/List segmented control.
  - Interactions: click a node to focus it, hover to preview and highlight
    neighbors, drag, zoom, pan, keyboard navigation between nodes, "F" to fit,
    Esc to clear focus.
  - Works with zero connections: nodes still look intentional, with a hint on
    how to create links.
- Auth pages: centered or split layout on the near-black background with a
  subtle accent glow, clear validation states, and a link back to the landing
  page.
- Global polish: skeleton loaders, toast notifications, illustrated empty
  states with a clear action (line-art style in the same palette), thin custom
  scrollbars, accent-colored text selection, a styled 404 page, and consistent
  hover and focus rings (1px accent border plus a faint glow).

## Part 3: Landing page for logged-out visitors

Routing rules:
- "/" for an unauthenticated visitor renders the landing page. For an
  authenticated user, "/" renders the Notes list (the authenticated home). Never
  flash the landing page to a logged-in user; resolve auth state first and show
  a neutral skeleton while checking.
- Protected routes (Notes, Suggestions, Graph, note editor) redirect
  unauthenticated users to sign-in and return them to the intended page after
  signing in.
- A logged-in user visiting sign-in or sign-up is redirected to the Notes list.
- Landing navbar: logo mark and wordmark, anchor links (Features, How it works,
  FAQ), theme toggle, "Sign in" (ghost) and "Get started" (primary orange).
  Collapses to a mobile menu.

Landing visual style (mirror the reference's presentation):
- The hero background is a large warm gradient, from a lighter coral-orange at
  the top to a deeper red-orange at the bottom, with faint grain/noise for
  texture. Below the hero, sections return to the near-black theme.
- The hero visual is a floating "app window" mockup: a near-black window with a
  14 to 16px radius, 1px border, a large soft shadow, and generous gradient
  space around it. It contains a faithful, static recreation of the real UI
  (icon rail, sidebar with sections and counts, and a graph canvas with a lit
  orange focal node, dimmed outer nodes, solid and dashed edges, zoom capsule
  and legend). Build it from real components with mock data, not a screenshot
  or stock image. Add a subtle entrance animation (fade and slight rise), and
  optional gentle node drift or edge-draw animation.
- Headline typography: large, tight, white or near-black text on the gradient
  with strong contrast; a short subheadline in a lighter weight.

Sections, in order, with real specific copy (no lorem ipsum):
1. Hero: headline about connecting ideas (for example "Your notes,
   connected."), a one-sentence subheadline explaining that LinkNote turns
   Markdown notes into a knowledge graph by suggesting links between related
   ideas, primary CTA "Get started free" and secondary CTA "See how it works"
   (smooth scroll), then the app-window mockup.
2. Trust strip: a thin row of true claims such as "Markdown-first", "You approve
   every link", "Keyboard-friendly". No invented customer logos, user counts or
   testimonials.
3. Features: 3 to 6 bordered cards on near-black with thin line icons: Markdown
   editor with live preview, tags and fast search, smart link suggestions,
   interactive knowledge graph, accept/reject control ("Nothing is linked until
   you decide"), keyboard-first writing.
4. How it works: three numbered steps (Write, Review suggested links, Explore
   your graph) each with a small cropped slice of the real UI styling.
5. Product showcase: a tabbed (Notes / Suggestions / Graph) interactive preview
   using static mock data in the same app-window frame.
6. FAQ: accessible accordion with 4 to 6 truthful questions; mark anything
   uncertain with a TODO comment instead of inventing details.
7. Final call to action: a gradient band reusing the hero's orange gradient,
   with a headline and a "Get started free" button.
8. Footer: logo mark, tagline, links, dynamic copyright year.

Landing quality requirements:
- Scroll-triggered fade/slide reveals via IntersectionObserver (disabled under
  prefers-reduced-motion).
- Responsive from 360px to wide desktop; on mobile the app-window mockup scales
  down and may crop, keeping the lit focal node visible.
- Performance: no layout shift, lazy-load below-the-fold content, inline or
  optimize SVGs, aim for Lighthouse 90+ in performance, accessibility and best
  practices.
- SEO: title, meta description, Open Graph and Twitter tags, canonical URL,
  semantic HTML (one h1, ordered headings, landmarks), favicon set.
- Accessibility: keyboard navigable, skip link, visible focus, WCAG AA contrast
  (verify white text on the gradient; darken the gradient or add a scrim if
  needed), decorative graphics marked aria-hidden.

## Constraints
- Prefer CSS and SVG over heavy dependencies. A small well-known icon library
  and a graph library are acceptable if already used or clearly justified.
- Keep the accent usage disciplined as described; do not introduce additional
  bright colors.
- No tracking scripts or external network calls added for visuals. Self-host
  fonts if possible.
- Do not break authentication, existing routes or existing data.

## Deliverables and process
1. First reply with a short plan: styling approach, files to create or change,
   route/auth guard strategy, and the graph layout approach.
2. Implement in this order, one commit each: (a) tokens and primitives, (b) app
   shell and restyled authenticated pages including the Graph, (c) auth pages,
   (d) landing page and routing rules.
3. Add tests for routing: logged-out "/" shows landing, logged-in "/" shows
   Notes, protected routes redirect with a return path, logged-in users are
   redirected away from sign-in and sign-up.
4. Finish with a summary and a manual checklist: check each page in dark and
   light themes at mobile and desktop widths, tab through the landing page with
   the keyboard, verify contrast of text on the orange gradient, and verify the
   logged-in and logged-out redirects.