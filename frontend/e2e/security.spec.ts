import { expect, test } from "@playwright/test";

import { createNoteViaApi, signUpViaApi } from "./helpers";

test("session cookies are HttpOnly and invisible to page scripts", async ({ page }) => {
  await signUpViaApi(page.request);
  await page.goto("/notes");
  await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();

  const cookies = await page.context().cookies();
  const session = cookies.filter((c) => c.name === "access_token" || c.name === "refresh_token");
  expect(session.map((c) => c.name).sort()).toEqual(["access_token", "refresh_token"]);
  for (const cookie of session) {
    expect(cookie.httpOnly).toBe(true);
    expect(cookie.sameSite).toBe("Lax");
  }
  expect(await page.evaluate(() => document.cookie)).not.toMatch(/access_token|refresh_token/);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toMatch(/eyJ/);
});

test("note content cannot run script in the preview or on the page", async ({ page }) => {
  await signUpViaApi(page.request);
  const dialogs: string[] = [];
  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });

  const note = await createNoteViaApi(page.request, {
    title: "<img src=x onerror=alert('title')> hostile title",
    body: [
      "<script>alert('script')</script>",
      "<img src=x onerror=\"alert('img')\">",
      "[js link](javascript:alert('link'))",
      "[fine](https://example.com)",
    ].join("\n\n"),
  });

  await page.goto(`/notes/${note.id}`);
  await page.getByRole("button", { name: "preview" }).click();
  const preview = page.getByLabel("Preview");
  await expect(preview.getByRole("link", { name: "fine" })).toHaveAttribute("href", "https://example.com");
  await expect(preview.locator("script, img")).toHaveCount(0);
  for (const href of await preview.getByRole("link").evaluateAll((links) => links.map((a) => a.getAttribute("href") ?? ""))) {
    expect(href).not.toMatch(/^javascript:/i);
  }

  // The hostile title is shown as text everywhere it appears.
  await page.goto("/notes");
  await expect(page.getByRole("link", { name: /hostile title/ })).toBeVisible();
  await page.goto("/graph");
  await page.getByRole("button", { name: "list", exact: true }).click();
  await expect(page.getByRole("link", { name: /hostile title/ })).toBeVisible();
  expect(dialogs).toEqual([]);
});

test("a user cannot reach another user's note", async ({ browser }) => {
  const alice = await browser.newContext();
  const bob = await browser.newContext();
  try {
    await signUpViaApi(alice.request);
    await signUpViaApi(bob.request);
    const note = await createNoteViaApi(alice.request, { title: "Alice private", body: "secret plans" });

    expect((await bob.request.get(`/api/notes/${note.id}`)).status()).toBe(404);
    expect((await bob.request.delete(`/api/notes/${note.id}`)).status()).toBe(404);

    const page = await bob.newPage();
    await page.goto(`/notes/${note.id}`);
    await expect(page.getByText("Note not found")).toBeVisible();
    await expect(page.getByText("Alice private")).toHaveCount(0);
    await expect(page.getByText("secret plans")).toHaveCount(0);
  } finally {
    await alice.close();
    await bob.close();
  }
});

test("API calls without a session are refused and private pages show nothing", async ({ page, request }) => {
  for (const path of ["/api/notes", "/api/tags", "/api/suggestions", "/api/links", "/api/graph", "/api/auth/me"]) {
    expect((await request.get(path)).status(), path).toBe(401);
  }
  await page.goto("/graph");
  await expect(page).toHaveURL(/\/login\?next=%2Fgraph/);
  await expect(page.getByText("Knowledge graph")).toHaveCount(0);
});

test("the login redirect never leaves the site", async ({ page }) => {
  await page.goto("/login?next=//evil.example/steal");
  const email = await signUpViaApi(page.request);
  expect(email).toBeTruthy();
  await page.goto("/login?next=//evil.example/steal");
  // Already signed in via the API cookies; signing in again must still land on a local page.
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct horse battery staple");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/localhost.*\/notes$/);
});

test("an expired session is refreshed transparently", async ({ page, context }) => {
  await signUpViaApi(page.request);
  await page.goto("/notes");
  await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();

  // Drop only the short-lived access token, as if its 15 minutes had passed.
  const cookies = await context.cookies();
  await context.clearCookies({ name: "access_token" });
  expect(cookies.some((c) => c.name === "refresh_token")).toBe(true);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();
  expect((await context.cookies()).some((c) => c.name === "access_token")).toBe(true);
});
