import { expect, test } from "@playwright/test";

import { PASSWORD, createNoteViaUi, uniqueEmail } from "./helpers";

test("a new user registers, writes notes, accepts a suggestion, and sees the link in the graph", async ({ page }) => {
  const email = uniqueEmail();

  // Private pages send visitors to sign in and bring them back afterwards.
  await page.goto("/notes");
  await expect(page).toHaveURL(/\/login\?next=%2Fnotes/);

  // Register.
  await page.getByRole("link", { name: "Create one" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/notes$/);
  await expect(page.getByText("You have no notes yet")).toBeVisible();

  // Write two related notes and one unrelated one.
  await createNoteViaUi(page, {
    title: "Kubernetes deployment strategies",
    body: "Rolling updates for **kubernetes** deployment pods and services with health probes.",
    tags: ["devops", "k8s"],
  });
  await createNoteViaUi(page, {
    title: "Kubernetes deployments",
    body: "kubernetes deployment rolling updates pods services",
    tags: ["devops"],
  });
  await createNoteViaUi(page, { title: "Sourdough baking", body: "flour water salt starter oven crust", tags: ["food"] });

  // Search and tag filters on the notes page.
  await page.goto("/notes");
  await expect(page.getByRole("list", { name: "Notes" }).getByRole("listitem")).toHaveCount(3);
  await page.getByRole("searchbox", { name: "Search notes" }).fill("sourdough");
  await expect(page.getByRole("list", { name: "Notes" }).getByRole("listitem")).toHaveCount(1);
  await page.getByRole("searchbox", { name: "Search notes" }).fill("");
  await page.getByRole("button", { name: /^devops/ }).click();
  await expect(page.getByRole("list", { name: "Notes" }).getByRole("listitem")).toHaveCount(2);
  await page.getByRole("button", { name: /^k8s/ }).click(); // devops AND k8s
  await expect(page.getByRole("list", { name: "Notes" }).getByRole("listitem")).toHaveCount(1);

  // Suggestions arrive asynchronously through the outbox, Redis and the link worker.
  await page.getByRole("link", { name: "Suggestions" }).click();
  await expect(page).toHaveURL(/\/suggestions$/);
  await expect(async () => {
    await page.reload();
    await expect(page.getByRole("heading", { name: "Link suggestions (1)" })).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 45_000, intervals: [1_000] });
  const card = page.getByRole("listitem").filter({ hasText: "Kubernetes deployments" });
  await expect(card).toContainText("% match");
  await expect(card).toContainText("Shared keywords");
  await expect(card.getByRole("link", { name: "Sourdough baking" })).toHaveCount(0);

  await card.getByRole("button", { name: /^Accept/ }).click();
  await expect(page.getByRole("status").filter({ hasText: "Linked" })).toBeVisible();
  await expect(page.getByText("No suggestions to review")).toBeVisible();

  // The accepted link is in the graph, drawn on a canvas and also available as an accessible list.
  await page.getByRole("link", { name: "Graph" }).click();
  await expect(page.getByText("3 notes, 1 connection")).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();
  await page.getByRole("button", { name: "list", exact: true }).click();
  const list = page.getByRole("list", { name: "Notes and their connections" });
  await expect(list.getByRole("listitem").filter({ hasText: /^\s*Kubernetes deployments/ })).toContainText(
    "Connected to: Kubernetes deployment strategies",
  );
  await expect(list.getByRole("listitem").filter({ hasText: "Sourdough baking" })).toContainText(
    "Not connected to other notes.",
  );

  // A tag filter restricts the graph through the backend.
  await page.getByRole("button", { name: /^food/ }).click();
  await expect(page.getByText("1 note, 0 connections")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();

  // Follow a link from the graph to the note; the note shows its linked note.
  await page.getByRole("link", { name: "Kubernetes deployments" }).first().click();
  await expect(page.getByRole("heading", { name: "Edit note" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Linked notes" })).toContainText("Kubernetes deployment strategies");

  // Edit, then delete with confirmation.
  await page.getByLabel("Title").fill("Kubernetes rollouts");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();
  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByRole("button", { name: "Yes, delete" }).click();
  await expect(page).toHaveURL(/\/notes$/);
  await expect(page.getByRole("list", { name: "Notes" }).getByRole("listitem")).toHaveCount(2);

  // Sign out closes the session; signing back in restores access.
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/notes");
  await expect(page).toHaveURL(/\/login\?next=%2Fnotes/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/notes$/);
  await expect(page.getByRole("list", { name: "Notes" }).getByRole("listitem")).toHaveCount(2);
});

test("a rejected suggestion stays dismissed", async ({ page }) => {
  await page.goto("/register");
  const email = uniqueEmail();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/notes$/);

  await createNoteViaUi(page, { title: "Postgres indexing guide", body: "btree gin indexes planner statistics vacuum" });
  await createNoteViaUi(page, { title: "Postgres index tuning", body: "gin btree indexes planner statistics" });

  await page.goto("/suggestions");
  await expect(async () => {
    await page.reload();
    await expect(page.getByRole("heading", { name: "Link suggestions (1)" })).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 45_000, intervals: [1_000] });
  await page.getByRole("button", { name: /^Reject/ }).click();
  await expect(page.getByText("No suggestions to review")).toBeVisible();

  await page.reload();
  await expect(page.getByText("No suggestions to review")).toBeVisible();
  await page.goto("/graph");
  await expect(page.getByText("2 notes, 0 connections")).toBeVisible();
});
