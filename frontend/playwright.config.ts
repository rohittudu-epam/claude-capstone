import { defineConfig, devices } from "@playwright/test";

// These tests drive the real stack, so start it first: `docker compose up -d --build` (see docs/testing.md).
// E2E_BASE_URL points at the reverse proxy that serves both the UI and the API.
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
