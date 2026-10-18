import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { randomBytes } from "node:crypto";

export const PASSWORD = "correct horse battery staple";

export function uniqueEmail(): string {
  return `e2e-${Date.now()}-${randomBytes(3).toString("hex")}@example.com`;
}

/** Registers and signs in through the API; the browser context keeps the session cookies. */
export async function signUpViaApi(request: APIRequestContext, email = uniqueEmail()): Promise<string> {
  const registered = await request.post("/api/auth/register", { data: { email, password: PASSWORD } });
  expect(registered.status()).toBe(201);
  const login = await request.post("/api/auth/login", { data: { email, password: PASSWORD } });
  expect(login.status()).toBe(200);
  return email;
}

export async function createNoteViaApi(
  request: APIRequestContext,
  note: { title: string; body: string; tags?: string[] },
): Promise<{ id: string }> {
  const response = await request.post("/api/notes", { data: { tags: [], ...note } });
  expect(response.status()).toBe(201);
  return response.json();
}

/** Writes a note through the UI form and waits for it to be saved. */
export async function createNoteViaUi(page: Page, note: { title: string; body: string; tags?: string[] }) {
  await page.goto("/notes/new");
  await page.getByLabel("Title").fill(note.title);
  await page.getByLabel("Markdown text").fill(note.body);
  for (const tag of note.tags ?? []) {
    const input = page.getByRole("combobox", { name: "Tags" });
    await input.fill(tag);
    await input.press("Enter");
  }
  await page.getByRole("button", { name: "Create note" }).click();
  await expect(page).toHaveURL(/\/notes$/);
  await expect(page.getByText("Note created")).toBeVisible();
}
