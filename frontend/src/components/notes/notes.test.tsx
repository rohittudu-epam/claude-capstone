import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NoteEditor } from "@/components/notes/note-editor";
import { NotesBrowser } from "@/components/notes/notes-browser";
import { NoteView } from "@/components/notes/note-view";
import { note, noteSummary, page, tag } from "@/test/fixtures";
import { router, state } from "@/test/navigation-mock";
import { mockFetch, renderWithClient } from "@/test/utils";

vi.mock("next/navigation", async () => (await import("@/test/navigation-mock")).navigationModule);

beforeEach(() => {
  state.pathname = "/notes";
  state.search = "";
});

const TAGS = { "GET /api/tags": { json: [tag("devops", 2), tag("backend", 1)] } };

describe("NoteEditor", () => {
  it("requires a title and does not call the API", async () => {
    const { to } = mockFetch(TAGS);
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.click(screen.getByRole("button", { name: "Create note" }));
    expect(screen.getByText("Give the note a title.")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveAttribute("aria-invalid", "true");
    expect(to("POST", "/api/notes")).toHaveLength(0);
  });

  it("creates a note with normalised, de-duplicated tags and returns to the list", async () => {
    const { to } = mockFetch({
      ...TAGS,
      "POST /api/notes": { status: 201, json: note({ id: "new-id" }) },
    });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.type(screen.getByLabelText("Title"), "  My note  ");
    await user.type(screen.getByLabelText("Markdown text"), "# Heading");
    const tagBox = screen.getByLabelText("Tags");
    await user.type(tagBox, "  DevOps {Enter}");
    await user.type(tagBox, "devops{Enter}");
    await user.type(tagBox, "Dev   Ops,");
    expect(within(screen.getByRole("list", { name: "Selected tags" })).getAllByRole("listitem")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Create note" }));

    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/notes"));
    expect(to("POST", "/api/notes")[0]?.body).toEqual({ title: "My note", body: "# Heading", tags: ["devops", "dev ops"] });
  });

  it("focuses the title, and creates only one note on rapid double submit", async () => {
    const { to } = mockFetch({ ...TAGS, "POST /api/notes": { status: 201, json: note({ id: "n9" }) } });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    expect(screen.getByLabelText("Title")).toHaveFocus();
    await user.type(screen.getByLabelText("Title"), "Once");
    const button = screen.getByRole("button", { name: "Create note" });
    await user.dblClick(button);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/notes"));
    expect(to("POST", "/api/notes")).toHaveLength(1);
  });

  it("saves with Ctrl+Enter", async () => {
    const { to } = mockFetch({ ...TAGS, "POST /api/notes": { status: 201, json: note({ id: "n8" }) } });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.type(screen.getByLabelText("Title"), "Quick{Control>}{Enter}{/Control}");
    await waitFor(() => expect(to("POST", "/api/notes")).toHaveLength(1));
  });

  it("cancels immediately when untouched and asks first when there is input", async () => {
    mockFetch(TAGS);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    router.push.mockClear();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(confirm).not.toHaveBeenCalled();
    expect(router.push).toHaveBeenCalledWith("/notes");

    router.push.mockClear();
    await user.type(screen.getByLabelText("Title"), "draft");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(router.push).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Title")).toHaveValue("draft");

    confirm.mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(router.push).toHaveBeenCalledWith("/notes");
    confirm.mockRestore();
  });

  it("does not submit the form when Enter is pressed in the tag box", async () => {
    const { to } = mockFetch(TAGS);
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.type(screen.getByLabelText("Title"), "Title");
    await user.type(screen.getByLabelText("Tags"), "one{Enter}");
    expect(to("POST", "/api/notes")).toHaveLength(0);
  });

  it("removes a tag with its button and with Backspace", async () => {
    mockFetch(TAGS);
    const user = userEvent.setup();
    renderWithClient(<NoteEditor note={note({ tags: ["a", "b", "c"] })} />);
    await user.click(screen.getByRole("button", { name: "Remove tag a" }));
    await user.click(screen.getByLabelText("Tags"));
    await user.keyboard("{Backspace}");
    const remaining = within(screen.getByRole("list", { name: "Selected tags" })).getAllByRole("listitem");
    expect(remaining.map((li) => li.textContent?.replace("×", ""))).toEqual(["b"]);
  });

  it("limits tag length and count", async () => {
    mockFetch(TAGS);
    const user = userEvent.setup();
    renderWithClient(<NoteEditor note={note({ tags: Array.from({ length: 20 }, (_, i) => `t${i}`) })} />);
    await user.type(screen.getByLabelText("Tags"), "one more{Enter}");
    expect(screen.getByText("A note can have at most 20 tags.")).toBeInTheDocument();
  });

  it("previews Markdown as rendered HTML", async () => {
    mockFetch(TAGS);
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.type(screen.getByLabelText("Markdown text"), "# Big heading{Enter}{Enter}- item one");
    await user.click(screen.getByRole("button", { name: "preview" }));
    expect(screen.getByRole("heading", { name: "Big heading", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("item one");
    await user.click(screen.getByRole("button", { name: "write" }));
    expect(screen.getByLabelText("Markdown text")).toHaveValue("# Big heading\n\n- item one");
  });

  it("never renders raw HTML or script-bearing links from note text", async () => {
    mockFetch(TAGS);
    const user = userEvent.setup();
    renderWithClient(
      <NoteEditor
        note={note({
          body: '<script>window.__pwned = true</script><img src=x onerror="window.__pwned = true">\n\n[click](javascript:alert(1)) and [ok](https://example.com)',
        })}
      />,
    );
    await user.click(screen.getByRole("button", { name: "preview" }));
    const preview = screen.getByLabelText("Preview");
    expect(preview.querySelector("script")).toBeNull();
    expect(preview.querySelector("img")).toBeNull();
    expect((window as unknown as { __pwned?: boolean }).__pwned).toBeUndefined();
    const links = within(preview).getAllByRole("link");
    for (const link of links) expect(link.getAttribute("href") ?? "").not.toMatch(/^javascript:/i);
    const safe = within(preview).getByRole("link", { name: "ok" });
    expect(safe).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(safe).toHaveAttribute("target", "_blank");
  });

  it("updates an existing note, confirms it, and offers no navigation away", async () => {
    const { to } = mockFetch({
      ...TAGS,
      "PUT /api/notes/n1": { json: note({ title: "Renamed" }) },
    });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor note={note()} />);
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Renamed");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Saved.");
    expect(to("PUT", "/api/notes/n1")[0]?.body).toMatchObject({ title: "Renamed", body: "# Pods\nbody text" });
    expect(router.push).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText("Title"), "!");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("maps server validation errors to their fields", async () => {
    mockFetch({
      ...TAGS,
      "POST /api/notes": {
        status: 400,
        json: { detail: "Invalid request", errors: [{ field: "tags.0", message: "tags must not be blank" }] },
      },
    });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.type(screen.getByLabelText("Title"), "x");
    await user.click(screen.getByRole("button", { name: "Create note" }));
    expect(await screen.findByText("tags must not be blank")).toBeInTheDocument();
  });

  it("shows a failure without losing what was typed", async () => {
    mockFetch({ ...TAGS, "POST /api/notes": { status: 500, json: { detail: "boom", correlation_id: "ref-7" } } });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor />);
    await user.type(screen.getByLabelText("Title"), "Keep me");
    await user.click(screen.getByRole("button", { name: "Create note" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("reference ref-7");
    expect(screen.getByLabelText("Title")).toHaveValue("Keep me");
    expect(screen.getByRole("button", { name: "Create note" })).toBeEnabled();
  });

  it("asks for confirmation before deleting, then returns to the list", async () => {
    const { to } = mockFetch({ ...TAGS, "DELETE /api/notes/n1": { status: 204 } });
    const user = userEvent.setup();
    renderWithClient(<NoteEditor note={note()} />);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(to("DELETE", "/api/notes/n1")).toHaveLength(0);
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/notes"));
    expect(to("DELETE", "/api/notes/n1")).toHaveLength(1);
  });
});

describe("NoteView", () => {
  it("shows linked notes from either side of each link", async () => {
    mockFetch({
      ...TAGS,
      "GET /api/notes/n1": { json: note() },
      "GET /api/links": {
        json: page([
          { id: "l1", source_note: { id: "n1", title: "Me" }, target_note: { id: "n2", title: "Other A" }, created_at: "" },
          { id: "l2", source_note: { id: "n3", title: "Other B" }, target_note: { id: "n1", title: "Me" }, created_at: "" },
        ]),
      },
    });
    renderWithClient(<NoteView id="n1" />);
    const section = await screen.findByRole("region", { name: "Linked notes" });
    expect(within(section).getByRole("link", { name: "Other A" })).toHaveAttribute("href", "/notes/n2");
    expect(within(section).getByRole("link", { name: "Other B" })).toHaveAttribute("href", "/notes/n3");
    expect(within(section).queryByRole("link", { name: "Me" })).not.toBeInTheDocument();
  });

  it("says so when the note does not exist", async () => {
    mockFetch({ ...TAGS, "GET /api/notes/missing": { status: 404, json: { detail: "Note not found" } } });
    renderWithClient(<NoteView id="missing" />);
    expect(await screen.findByText("Note not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to your notes" })).toHaveAttribute("href", "/notes");
  });
});

describe("NotesBrowser", () => {
  const list = (items = [noteSummary({ id: "n1", title: "First", tags: ["devops"] }), noteSummary({ id: "n2", title: "Second" })]) => ({
    "GET /api/notes": { json: page(items) },
  });

  it("shows a loading state, then the notes with tags and links", async () => {
    mockFetch({ ...TAGS, ...list() });
    renderWithClient(<NotesBrowser />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading notes…");
    const notes = await screen.findByRole("list", { name: "Notes" });
    expect(within(notes).getByRole("link", { name: "First" })).toHaveAttribute("href", "/notes/n1");
    expect(within(notes).getByText("devops")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("invites the user to write a first note when there are none", async () => {
    mockFetch({ "GET /api/tags": { json: [] }, "GET /api/notes": { json: page([]) } });
    renderWithClient(<NotesBrowser />);
    expect(await screen.findByText("You have no notes yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create your first note" })).toHaveAttribute("href", "/notes/new");
  });

  it("searches after a pause using the search endpoint, and says when nothing matches", async () => {
    const { to } = mockFetch({
      ...TAGS,
      ...list(),
      "GET /api/notes/search": { json: page([]) },
    });
    const user = userEvent.setup();
    renderWithClient(<NotesBrowser />);
    await screen.findByRole("list", { name: "Notes" });
    await user.type(screen.getByRole("searchbox", { name: "Search notes" }), "kubernetes");
    expect(to("GET", "/api/notes/search")).toHaveLength(0); // still inside the debounce window
    expect(await screen.findByText("No notes match your search")).toBeInTheDocument();
    const searches = to("GET", "/api/notes/search");
    expect(searches).toHaveLength(1);
    expect(searches[0]?.search.get("q")).toBe("kubernetes");
  });

  it("filters by several tags at once and can clear them", async () => {
    const { to } = mockFetch({ ...TAGS, ...list() });
    const user = userEvent.setup();
    renderWithClient(<NotesBrowser />);
    await screen.findByRole("list", { name: "Notes" });
    await user.click(screen.getByRole("button", { name: /devops/ }));
    await user.click(screen.getByRole("button", { name: /backend/ }));
    await waitFor(() => expect(to("GET", "/api/notes").at(-1)?.search.get("tags")).toBe("devops,backend"));
    expect(screen.getByRole("button", { name: /devops/ })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(to("GET", "/api/notes").at(-1)?.search.has("tags")).toBe(false));
  });

  it("combines search text with tag filters", async () => {
    const { to } = mockFetch({ ...TAGS, ...list(), "GET /api/notes/search": { json: page([noteSummary()]) } });
    const user = userEvent.setup();
    renderWithClient(<NotesBrowser />);
    await screen.findByRole("list", { name: "Notes" });
    await user.type(screen.getByRole("searchbox"), "pods");
    await user.click(screen.getByRole("button", { name: /devops/ }));
    await waitFor(() => {
      const last = to("GET", "/api/notes/search").at(-1);
      expect(last?.search.get("q")).toBe("pods");
      expect(last?.search.get("tags")).toBe("devops");
    });
  });

  it("pages through results", async () => {
    const { to } = mockFetch({
      ...TAGS,
      "GET /api/notes": (req) => ({
        json: { ...page([noteSummary({ id: req.search.get("offset") ?? "0", title: `Page ${req.search.get("offset")}` })], 45) },
      }),
    });
    const user = userEvent.setup();
    renderWithClient(<NotesBrowser />);
    expect(await screen.findByText("Showing 1–20 of 45")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Showing 21–40 of 45")).toBeInTheDocument();
    expect(to("GET", "/api/notes").at(-1)?.search.get("offset")).toBe("20");
  });

  it("shows an error with a retry that recovers", async () => {
    let calls = 0;
    mockFetch({
      ...TAGS,
      "GET /api/notes": () => (++calls === 1 ? { status: 503, json: { detail: "Service temporarily unavailable" } } : { json: page([noteSummary()]) }),
    });
    const user = userEvent.setup();
    renderWithClient(<NotesBrowser />);
    expect(await screen.findByRole("alert")).toHaveTextContent("having trouble");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("list", { name: "Notes" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
