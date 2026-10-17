import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { createNoteViaApi, signUpViaApi } from "./helpers";

async function expectNoSeriousViolations(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const summary = serious.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
  expect(summary, `${label} has accessibility violations`).toEqual([]);
}

test.describe("accessibility (WCAG 2.1 A/AA, serious and critical issues)", () => {
  test("sign-in and registration", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expectNoSeriousViolations(page, "login");

    await page.getByRole("button", { name: "Sign in" }).click(); // show validation errors too
    await expect(page.getByText("Enter a valid email address.")).toBeVisible();
    await expectNoSeriousViolations(page, "login with errors");

    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    await expectNoSeriousViolations(page, "register");
  });

  test("notes, editor, suggestions and graph", async ({ page }) => {
    await signUpViaApi(page.request);
    const note = await createNoteViaApi(page.request, {
      title: "Kubernetes deployment",
      body: "# Heading\n\n- item\n\n[link](https://example.com)",
      tags: ["devops"],
    });
    await createNoteViaApi(page.request, { title: "Kubernetes deployments", body: "kubernetes deployment", tags: ["devops"] });

    await page.goto("/notes");
    await expect(page.getByRole("list", { name: "Notes" })).toBeVisible();
    await expectNoSeriousViolations(page, "notes list");

    await page.goto(`/notes/${note.id}`);
    await expect(page.getByLabel("Title")).toBeVisible();
    await expectNoSeriousViolations(page, "note editor (write)");
    await page.getByRole("button", { name: "preview" }).click();
    await expectNoSeriousViolations(page, "note editor (preview)");

    await page.goto("/suggestions");
    await expect(page.getByRole("heading", { name: /Link suggestions/ })).toBeVisible();
    await expectNoSeriousViolations(page, "suggestions");

    await page.goto("/graph");
    await expect(page.locator("canvas")).toBeVisible();
    await expectNoSeriousViolations(page, "graph (canvas view)");
    await page.getByRole("button", { name: "list", exact: true }).click();
    await expectNoSeriousViolations(page, "graph (list view)");
  });

  test("the whole app can be driven from the keyboard", async ({ page }) => {
    await signUpViaApi(page.request);
    await createNoteViaApi(page.request, { title: "Keyboard note", body: "text" });
    await page.goto("/notes");
    await expect(page.getByRole("list", { name: "Notes" })).toBeVisible();

    await page.keyboard.press("Tab"); // first stop is the skip link
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    await page.keyboard.press("Enter");

    await page.getByRole("link", { name: "Graph" }).focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/graph$/);
    await page.getByRole("button", { name: "Switch to the accessible list view" }).focus();
    await page.keyboard.press("Enter");
    const link = page.getByRole("list", { name: "Notes and their connections" }).getByRole("link", { name: "Keyboard note" });
    await link.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/notes\/[0-9a-f-]{36}$/);
  });
});
