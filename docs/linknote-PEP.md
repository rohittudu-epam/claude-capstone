# LinkNote: Enhancement User Stories

**Product:** LinkNote, a Markdown note-taking app with tags, link suggestions and a knowledge graph
**Scope:** Bug fixes, feature enhancements and visual polish
**Format:** Each story has a statement, acceptance criteria (Given/When/Then), and notes. Priorities use MoSCoW (Must / Should / Could).

---

## Current State (Observed)

| Area | Observed behavior |
|---|---|
| Create note | After clicking **Create note**, the user is not redirected to the Notes list. |
| Navbar | The "LinkNote" logo is plain text and does not link to home. |
| Suggestions | Page shows "Link suggestions (0)" even though 3 of 5 notes share the tags `ai`, `automation` and `machine learning`. |
| Linking | No way to manually link notes. |
| Graph | Shows "5 notes, 0 connections". Nodes are scattered with no edges. |

## Personas

- **Note Taker**: the primary user who writes notes, tags them and wants related ideas connected.
- **Researcher**: has many notes and relies on the graph and suggestions to discover relationships.
- **Keyboard / Assistive-tech User**: navigates without a mouse or with a screen reader.
- **Mobile User**: captures and reviews notes on a small screen.

## Epic Overview

| Epic | Title | Priority |
|---|---|---|
| E1 | Note creation and navigation flow | Must |
| E2 | Brand and global navigation | Must |
| E3 | Link suggestions engine | Must |
| E4 | Manual note linking | Must |
| E5 | Knowledge graph | Must |
| E6 | Visual design system | Should |
| E7 | Notes list experience | Should |
| E8 | Note editor experience | Should |
| E9 | Feedback, motion, responsiveness and accessibility | Should |
| E10 | Quality, testing and data safety | Must |

---

## E1. Note Creation and Navigation Flow

### US-1.1: Redirect to the notes list after creating a note
**As a** Note Taker,
**I want** to be taken back to the Notes list after I click "Create note",
**so that** I can immediately see my new note and know the save worked.

**Acceptance criteria**
- **Given** I have entered a valid title and body, **when** I click "Create note" and the save succeeds, **then** I am redirected to the Notes list (`/`).
- **Given** the redirect has happened, **then** my new note appears at the top of the list with the correct title, tags and timestamp.
- **Given** the save fails (validation or server error), **then** I stay on the form, see an inline error, and none of my input is lost.
- **Given** the save succeeds, **then** a toast "Note created" is shown for about 3 seconds.

**Priority:** Must

### US-1.2: Prevent duplicate submissions
**As a** Note Taker,
**I want** the "Create note" button to show a loading state and become disabled while saving,
**so that** double-clicking or a slow network does not create duplicate notes.

**Acceptance criteria**
- **Given** I click "Create note", **then** the button is disabled and shows a spinner or "Saving…" until the request completes.
- **Given** I click rapidly several times, **then** only one note is created.
- **Given** the request fails, **then** the button is re-enabled so I can retry.

**Priority:** Must

### US-1.3: Always be able to start a new note
**As a** Note Taker,
**I want** a "New note" action available from every page,
**so that** I can capture an idea without navigating back first.

**Acceptance criteria**
- **Given** I am on any page (Notes, Suggestions, Graph, a note detail view), **then** a "+ New note" button is visible in the navbar.
- **Given** I click it, **then** I land on the empty New note form with the title field focused.
- **Given** I am on the Notes page, **then** the existing "New note" button remains visible.
- **Given** I am viewing the list and it is empty, **then** an empty state offers a "Create your first note" button.

**Priority:** Must

### US-1.4: Cancel note creation safely
**As a** Note Taker,
**I want** a Cancel button on the note form,
**so that** I can leave without saving and not lose work by accident.

**Acceptance criteria**
- **Given** the form is untouched, **when** I click Cancel, **then** I return to the Notes list immediately.
- **Given** I have typed content, **when** I click Cancel or navigate away, **then** I am asked to confirm discarding changes.
- **Given** I confirm, **then** my input is discarded and I return to the list. **Given** I decline, **then** I stay on the form with my input intact.

**Priority:** Should

### US-1.5: Consistent behavior when editing a note
**As a** Note Taker,
**I want** the same save-and-return behavior when I edit an existing note,
**so that** the app behaves predictably.

**Acceptance criteria**
- **Given** I edit a note and click Save, **then** the update is persisted, a toast "Note updated" appears, and I return to the Notes list (or the note detail view).
- **Given** the note was updated, **then** its "Updated" timestamp reflects the change.
- **Given** the edit changes tags or content, **then** link suggestions are re-evaluated (see US-3.1).

**Priority:** Should

---

## E2. Brand and Global Navigation

### US-2.1: Logo links to the home page
**As a** Note Taker,
**I want** to click the "LinkNote" logo to go to the Notes list,
**so that** I have a familiar, one-click way home from anywhere in the app.

**Acceptance criteria**
- **Given** I am on any page, **when** I click the logo or wordmark, **then** I navigate to the Notes list (`/`) without a full page reload.
- **Given** I hover or keyboard-focus the logo, **then** it shows a visible hover and focus state.
- **Given** a screen reader is in use, **then** the link is announced with an accessible label such as "LinkNote, go to notes".
- **Given** I middle-click or Ctrl/Cmd-click, **then** it opens in a new tab (it is a real link, not a click handler).

**Priority:** Must

### US-2.2: Clear active navigation state
**As a** Note Taker,
**I want** the current section highlighted in the navbar,
**so that** I always know where I am.

**Acceptance criteria**
- **Given** I am on Notes, Suggestions or Graph, **then** the matching nav item is visibly highlighted and has `aria-current="page"`.
- **Given** I am on a sub-route (e.g. a note's edit page), **then** the parent section (Notes) remains highlighted.

**Priority:** Should

### US-2.3: Pending-suggestion badge in the navbar
**As a** Researcher,
**I want** a count badge on the Suggestions nav item,
**so that** I know when there are connections waiting for review.

**Acceptance criteria**
- **Given** there are N pending suggestions (N > 0), **then** the Suggestions nav item shows a badge with N (capped at "99+").
- **Given** N is 0, **then** no badge is shown.
- **Given** I accept or reject a suggestion, **then** the badge updates without a page reload.

**Priority:** Could

### US-2.4: User menu
**As a** Note Taker,
**I want** my account details and Sign out grouped in a user menu,
**so that** the navbar is less cluttered.

**Acceptance criteria**
- **Given** I am signed in, **then** the navbar shows an avatar with my initial instead of the raw email and a separate button.
- **Given** I click the avatar, **then** a menu opens showing my email and a "Sign out" action.
- **Given** the menu is open, **when** I press Escape or click outside, **then** it closes. It is fully keyboard operable.

**Priority:** Should

---

## E3. Link Suggestions Engine

### US-3.1: Suggestions are generated automatically when notes are saved
**As a** Note Taker,
**I want** the app to suggest links between notes that share tags or keywords,
**so that** I discover relationships I would otherwise miss.

**Acceptance criteria**
- **Given** I create or update a note, **then** the system compares it against all my other notes using shared tags plus keywords from the title and body.
- **Given** two notes exceed the match threshold, **then** a pending suggestion is created containing both note IDs, a score, and the list of shared keywords.
- **Given** the existing sample data (three notes sharing `ai`, `automation` and `machine learning`), **then** suggestions are produced between those notes.
- **Given** a pair already has a pending, accepted or rejected suggestion, **then** no duplicate is created.
- **Given** a note would be matched against itself, **then** no suggestion is created.
- **Given** the generation job runs asynchronously, **then** failures are logged and surfaced (not swallowed silently), and suggestions appear within a few seconds of saving.

**Notes:** Root-cause the current "0 suggestions" bug first. Check whether generation is triggered on save, whether a worker or job is running, whether the threshold is too strict, whether tags are being considered, and whether errors are being swallowed.

**Priority:** Must

### US-3.2: Backfill suggestions for existing notes
**As a** Note Taker with existing notes,
**I want** suggestions generated for notes I already have,
**so that** I benefit immediately without re-saving each note.

**Acceptance criteria**
- **Given** I have existing notes created before the fix, **when** the backfill runs (script, endpoint or on-demand button), **then** suggestions are generated for all eligible pairs.
- **Given** the backfill is run more than once, **then** it is idempotent and creates no duplicates.

**Priority:** Must

### US-3.3: Review suggestions with context
**As a** Researcher,
**I want** each suggestion to show why the two notes are related,
**so that** I can decide quickly whether the link is meaningful.

**Acceptance criteria**
- **Given** I open the Suggestions page, **then** each card shows both note titles, the shared keywords as chips, and a match score (percentage or bar).
- **Given** the heading "Link suggestions (N)", **then** N equals the number of pending suggestion cards.
- **Given** I click a note title on a card, **then** I can open that note (in a new tab or panel) to verify the match.
- **Given** the list is long, **then** it is sorted by score (highest first) and paginated or lazy loaded.

**Priority:** Must

### US-3.4: Accept a suggestion to create a link
**As a** Note Taker,
**I want** to accept a suggestion,
**so that** the two notes become linked in my graph.

**Acceptance criteria**
- **Given** I click Accept on a suggestion, **then** a persistent link between the two notes is created.
- **Given** the link is created, **then** the card animates out, the count decreases, and a toast "Notes linked" appears.
- **Given** I open the Graph, **then** a new edge connects the two notes and the connection count increases by one.
- **Given** the request fails, **then** the card remains and an error toast is shown.

**Priority:** Must

### US-3.5: Reject a suggestion permanently
**As a** Note Taker,
**I want** to reject a suggestion and never see it again,
**so that** irrelevant suggestions don't keep coming back.

**Acceptance criteria**
- **Given** I click Reject, **then** the suggestion is dismissed and the rejection is stored.
- **Given** either note is later edited, **then** the rejected pair is **not** re-suggested.
- **Given** I rejected by mistake, **then** a toast offers "Undo" for several seconds.

**Priority:** Must

### US-3.6: Refresh suggestions on demand
**As a** Researcher,
**I want** a "Refresh suggestions" button,
**so that** I can regenerate suggestions without editing a note.

**Acceptance criteria**
- **Given** I click Refresh, **then** a loading state is shown while suggestions are recomputed.
- **Given** it completes, **then** new suggestions appear and the count updates. If there are none, the empty state is shown.

**Priority:** Should

### US-3.7: Helpful empty state for Suggestions
**As a** Note Taker,
**I want** a clear empty state when there are no suggestions,
**so that** I understand why and what to do next.

**Acceptance criteria**
- **Given** there are no pending suggestions, **then** the page shows an icon, an explanation ("Add notes with shared tags or keywords to get suggestions"), and "Refresh" and "New note" actions.

**Priority:** Could

---

## E4. Manual Note Linking

### US-4.1: Link notes manually from a note
**As a** Note Taker,
**I want** to link one note to another myself,
**so that** I can connect ideas the system didn't suggest.

**Acceptance criteria**
- **Given** I am viewing or editing a note, **then** a "Linked notes" section is visible.
- **Given** I click "Add link", **then** a searchable picker lists my other notes (excluding the current note and already linked notes), filterable by title.
- **Given** I select a note, **then** the link is created and appears in the section immediately.
- **Given** I try to link a note to itself or to an already-linked note, **then** the action is prevented with a clear message.

**Priority:** Must

### US-4.2: Unlink notes
**As a** Note Taker,
**I want** to remove a link,
**so that** I can correct mistaken or outdated connections.

**Acceptance criteria**
- **Given** a linked note is listed, **when** I click the remove (x) control, **then** the link is deleted after a lightweight confirmation or an Undo toast.
- **Given** the link is removed, **then** the edge disappears from the Graph and the connection count decreases.

**Priority:** Must

### US-4.3: Bidirectional link display
**As a** Researcher,
**I want** links to appear on both connected notes,
**so that** I can navigate in either direction.

**Acceptance criteria**
- **Given** Note A is linked to Note B, **then** Note A's "Linked notes" lists B and Note B's lists A.
- **Given** I click a linked note's title, **then** I navigate to that note.

**Priority:** Must

---

## E5. Knowledge Graph

### US-5.1: Connections appear as edges
**As a** Researcher,
**I want** every accepted or manual link drawn as an edge in the graph,
**so that** I can see how my ideas relate.

**Acceptance criteria**
- **Given** links exist, **then** the Graph shows an edge for each one and the summary reads "N notes, M connections" with the correct M.
- **Given** a link is created or removed elsewhere in the app, **then** the Graph reflects it on next load (or live).
- **Given** no links exist, **then** a hint explains how to create links (accept suggestions or link manually).

**Priority:** Must

### US-5.2: Meaningful automatic layout
**As a** Researcher,
**I want** connected notes to cluster together,
**so that** the graph reveals structure instead of random scatter.

**Acceptance criteria**
- **Given** the graph loads, **then** a force-directed layout positions connected nodes near each other and keeps nodes within the visible canvas.
- **Given** the graph has isolated notes, **then** they remain visible and don't overlap labels.
- **Given** I use a "Reset view" control, **then** the graph re-centers and re-fits.

**Priority:** Must

### US-5.3: Interact with the graph
**As a** Researcher,
**I want** to drag, zoom, pan and click nodes,
**so that** I can explore larger graphs comfortably.

**Acceptance criteria**
- **Given** I drag a node, **then** it moves and connected nodes respond smoothly.
- **Given** I scroll or pinch, **then** the graph zooms. **Given** I drag the background, **then** it pans.
- **Given** I click a node, **then** that note opens.
- **Given** I hover a node, **then** its full title is shown (not truncated) and its neighbors and edges are highlighted while others dim.
- **Given** keyboard-only use, **then** nodes are focusable and Enter opens the note.

**Priority:** Should

### US-5.4: Node size reflects importance
**As a** Researcher,
**I want** more-connected notes drawn larger,
**so that** I can spot central ideas at a glance.

**Acceptance criteria**
- **Given** nodes have different numbers of connections, **then** node radius scales with connection count within a sensible min and max.

**Priority:** Could

### US-5.5: Filter the graph by tag
**As a** Researcher,
**I want** to click a tag chip to filter or highlight matching notes,
**so that** I can focus on one topic.

**Acceptance criteria**
- **Given** I click a tag chip, **then** matching nodes are highlighted (or non-matching ones hidden) and the chip appears selected.
- **Given** I click the chip again or "Clear filters", **then** the full graph returns.
- **Given** the "List" toggle is used, **then** the list view respects the same filter.

**Priority:** Should

---

## E6. Visual Design System

### US-6.1: Consistent design tokens
**As a** designer or developer maintaining the app,
**I want** colors, spacing, radii, shadows and type sizes defined as tokens,
**so that** the UI stays consistent and is easy to restyle.

**Acceptance criteria**
- **Given** the stylesheet, **then** colors, spacing (8px scale), radii (8 to 12px), shadows and font sizes come from CSS variables or a theme config, not hard-coded values.
- **Given** the palette, **then** it contains one accent color plus semantic success, warning and danger colors.
- **Given** the dark theme, **then** text and interactive elements meet WCAG AA contrast.

**Priority:** Should

### US-6.2: Refined typography
**As a** Note Taker,
**I want** a clear, readable type hierarchy,
**so that** the interface feels polished and scannable.

**Acceptance criteria**
- **Given** any page, **then** page titles, section labels, body text and metadata use distinct, consistent sizes and weights with a clean sans-serif font (e.g. Inter) and sensible fallbacks.

**Priority:** Should

### US-6.3: Polished sticky navbar
**As a** Note Taker,
**I want** a navbar that stays in view and looks refined,
**so that** navigation is always at hand.

**Acceptance criteria**
- **Given** I scroll, **then** the navbar stays at the top with a subtle blur and bottom border.
- **Given** the navbar, **then** it shows a logo icon with the wordmark, the nav items with active state, the "+ New note" button and the user menu.

**Priority:** Should

---

## E7. Notes List Experience

### US-7.1: Notes as informative cards
**As a** Note Taker,
**I want** each note shown with a preview and metadata,
**so that** I can recognize notes without opening them.

**Acceptance criteria**
- **Given** the Notes list, **then** each note card shows title, a 1 to 2 line content preview, tag chips and a link-count indicator.
- **Given** timestamps, **then** they display relatively ("2 min ago") with the full date and time on hover.
- **Given** I hover or focus a card, **then** it shows a clear hover and focus state and the entire card is clickable.

**Priority:** Should

### US-7.2: Sort notes
**As a** Note Taker,
**I want** to sort my notes,
**so that** I can find what I need quickly.

**Acceptance criteria**
- **Given** the sort control, **then** I can sort by Recently updated (default), Recently created, and Title A to Z.
- **Given** I change the sort, **then** the list updates and my choice persists across page loads.

**Priority:** Could

### US-7.3: Clear tag and search filters
**As a** Note Taker,
**I want** active filters to be obvious and easy to clear,
**so that** I never wonder why notes are missing.

**Acceptance criteria**
- **Given** I click a tag chip, **then** it appears selected and the list filters accordingly. Multiple tags can be combined.
- **Given** any filter or search is active, **then** a "Clear filters" action is visible.
- **Given** no notes match, **then** a "No notes match your filters" empty state is shown with a clear-filters action.

**Priority:** Should

### US-7.4: Loading skeletons
**As a** Note Taker,
**I want** skeleton placeholders while notes load,
**so that** the page doesn't feel blank or broken.

**Acceptance criteria**
- **Given** data is loading, **then** skeleton cards are shown in place of the list, and they are replaced without layout jump.

**Priority:** Could

---

## E8. Note Editor Experience

### US-8.1: Faster, friendlier tag entry
**As a** Note Taker,
**I want** tag chips with remove buttons and autocomplete,
**so that** tagging is quick and consistent.

**Acceptance criteria**
- **Given** I type a tag and press Enter (or comma), **then** it becomes a chip. Duplicates and empty tags are ignored.
- **Given** I type, **then** existing tags are suggested for selection.
- **Given** I click the x on a chip, or press Backspace in an empty tag input, **then** the tag is removed.

**Priority:** Should

### US-8.2: Markdown formatting toolbar
**As a** Note Taker,
**I want** a toolbar for common Markdown formatting,
**so that** I don't have to remember syntax.

**Acceptance criteria**
- **Given** the editor, **then** a toolbar offers bold, italic, heading, list, code and link actions.
- **Given** text is selected and I click an action, **then** the selection is wrapped or formatted correctly. **Given** nothing is selected, **then** a placeholder snippet is inserted.
- **Given** I use common shortcuts (e.g. Ctrl/Cmd+B, Ctrl/Cmd+I), **then** they apply the same formatting.

**Priority:** Could

### US-8.3: Clean Write/Preview toggle and word count
**As a** Note Taker,
**I want** a clear Write/Preview switch and a live word count,
**so that** I can check formatting and length as I go.

**Acceptance criteria**
- **Given** the editor, **then** Write and Preview appear as a segmented control with an obvious selected state.
- **Given** I switch to Preview, **then** the rendered Markdown matches what will display in the note view, and my text is preserved when switching back.
- **Given** I type, **then** a word count updates live.

**Priority:** Should

### US-8.4: Efficient form behavior
**As a** Note Taker,
**I want** the title focused on open and a keyboard shortcut to save,
**so that** capturing a note takes seconds.

**Acceptance criteria**
- **Given** the New note form opens, **then** the Title field is auto-focused.
- **Given** I press Ctrl/Cmd+Enter, **then** the note is saved (same behavior as US-1.1).
- **Given** a required field is empty, **then** an inline validation message identifies it.

**Priority:** Should

---

## E9. Feedback, Motion, Responsiveness and Accessibility

### US-9.1: Toast notifications for actions
**As a** Note Taker,
**I want** brief confirmations and errors,
**so that** I know whether my actions succeeded.

**Acceptance criteria**
- **Given** note create/update/delete, link/unlink, and accept/reject actions, **then** a toast confirms success or explains failure.
- **Given** a toast appears, **then** it auto-dismisses (except errors, which persist until dismissed), is announced to screen readers via a live region, and can be closed manually.

**Priority:** Should

### US-9.2: Smooth, restrained motion
**As a** Note Taker,
**I want** subtle transitions,
**so that** the app feels responsive without being distracting.

**Acceptance criteria**
- **Given** hover, focus and card removal, **then** transitions last roughly 150 to 200ms.
- **Given** my OS has "reduce motion" enabled (`prefers-reduced-motion`), **then** non-essential animations are disabled or minimized.

**Priority:** Should

### US-9.3: Mobile-friendly layout
**As a** Mobile User,
**I want** the app to work well on a small screen,
**so that** I can use it anywhere.

**Acceptance criteria**
- **Given** a viewport of about 375px, **then** content has no horizontal scrolling and tap targets are at least 44px.
- **Given** a narrow screen, **then** the navbar collapses into a menu that is easy to open and close.
- **Given** the Suggestions cards and note form, **then** they stack vertically and remain fully usable.
- **Given** the Graph on touch, **then** pinch-zoom, drag and tap work.

**Priority:** Should

### US-9.4: Keyboard and screen-reader accessibility
**As a** Keyboard / Assistive-tech User,
**I want** every feature usable without a mouse,
**so that** I can use LinkNote independently.

**Acceptance criteria**
- **Given** any interactive element, **then** it is reachable by Tab in a logical order and shows a visible focus ring.
- **Given** form fields, buttons and icons, **then** they have proper labels or `aria-label`s.
- **Given** dynamic changes (toasts, suggestion removal, count updates), **then** they are announced appropriately.
- **Given** text and UI components, **then** contrast meets WCAG AA.

**Priority:** Should

---

## E10. Quality, Testing and Data Safety

### US-10.1: Automated test coverage for new behavior
**As a** developer or QA engineer,
**I want** automated tests for the new flows,
**so that** regressions are caught early.

**Acceptance criteria**
- Unit/integration tests cover: suggestion generation (shared tags, shared keywords, threshold), duplicate and self-link prevention, accept, reject (including no re-suggestion), manual link/unlink, and graph edge data.
- UI or end-to-end tests cover: create note then redirect, logo navigates home, accept suggestion then edge appears in graph, and manual link then edge appears in graph.
- All tests run in CI and pass before merge.

**Priority:** Must

### US-10.2: Safe schema changes
**As a** developer,
**I want** database changes delivered as migrations,
**so that** existing users' data and authentication are never broken.

**Acceptance criteria**
- **Given** new tables (e.g. note links, rejected suggestions), **then** they are added via versioned migrations that are reversible where possible.
- **Given** the migration runs on existing data, **then** current notes, tags and user accounts are unchanged.
- **Given** link records, **then** they are scoped to the owning user so one user can never see or link another user's notes.

**Priority:** Must

### US-10.3: Observability for background suggestion jobs
**As a** developer,
**I want** suggestion generation failures to be logged and visible,
**so that** a broken worker can't silently produce "0 suggestions" again.

**Acceptance criteria**
- **Given** the generation job fails, **then** the error is logged with note IDs and a stack trace.
- **Given** the job succeeds, **then** a log line records how many suggestions were created.

**Priority:** Should

---

## Definition of Done (applies to every story)

- Acceptance criteria are met and verified manually and by automated tests where listed.
- UI changes are checked at desktop and mobile widths, keyboard-only, and with `prefers-reduced-motion`.
- No regressions to authentication or existing notes.
- Code reviewed and merged with a clear commit message referencing the story ID.

## Manual Verification Checklist (the three original issues)

1. **Redirect and new note:** Create a note, click "Create note", and confirm you land on the Notes list with the new note visible and a success toast. Confirm "+ New note" is available in the navbar on every page.
2. **Logo link:** From Suggestions, Graph and a note page, click the LinkNote logo and confirm it returns to the Notes list.
3. **Suggestions and graph:** Run the backfill, open Suggestions and confirm suggestions appear for the notes sharing `ai`, `automation` and `machine learning`. Accept one, then open Graph and confirm an edge appears with the connection count increased. Link two notes manually and confirm the same.
