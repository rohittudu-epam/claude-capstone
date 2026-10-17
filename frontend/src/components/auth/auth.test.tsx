import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthGate } from "@/components/auth/auth-gate";
import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";
import { mockFetch, renderWithClient } from "@/test/utils";
import { router, state } from "@/test/navigation-mock";

vi.mock("next/navigation", async () => (await import("@/test/navigation-mock")).navigationModule);

beforeEach(() => {
  state.pathname = "/notes";
  state.search = "";
});

async function fillLogin(user: ReturnType<typeof userEvent.setup>, email = "alice@example.com", password = "correct horse") {
  if (email) await user.type(screen.getByLabelText("Email"), email);
  if (password) await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginForm", () => {
  it("shows field errors and does not call the API when the form is invalid", async () => {
    const { calls } = mockFetch({});
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);
    await fillLogin(user, "not-an-email", "");
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(calls).toHaveLength(0);
  });

  it("signs in and goes to the notes page", async () => {
    const { calls } = mockFetch({
      "POST /api/auth/login": { json: { user_id: "u1", expires_in: 900 } },
      "GET /api/auth/me": { json: { id: "u1", email: "alice@example.com" } },
    });
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);
    await fillLogin(user);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/notes"));
    expect(calls[0]?.body).toEqual({ email: "alice@example.com", password: "correct horse" });
  });

  it("returns to the page the user was sent from, but only if it is a local path", async () => {
    mockFetch({ "POST /api/auth/login": { json: {} } });
    state.search = "next=%2Fgraph";
    const user = userEvent.setup();
    const { unmount } = renderWithClient(<LoginForm />);
    await fillLogin(user);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/graph"));
    unmount();

    router.push.mockClear();
    state.search = "next=%2F%2Fevil.example";
    renderWithClient(<LoginForm />);
    await fillLogin(user);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/notes"));
  });

  it("shows one generic message for wrong credentials", async () => {
    mockFetch({ "POST /api/auth/login": { status: 401, json: { detail: "Authentication failed" } } });
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);
    await fillLogin(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
    expect(router.push).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("explains rate limiting and network failures", async () => {
    const user = userEvent.setup();
    mockFetch({ "POST /api/auth/login": { status: 429, json: { detail: "Too Many Requests" } } });
    const { unmount } = renderWithClient(<LoginForm />);
    await fillLogin(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many attempts");
    unmount();

    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
    renderWithClient(<LoginForm />);
    await fillLogin(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the server");
  });

  it("disables the button while signing in so the form cannot be submitted twice", async () => {
    let release: () => void = () => {};
    const { calls } = mockFetch({
      "POST /api/auth/login": () => new Promise((resolve) => (release = () => resolve({ json: {} }))),
    });
    const user = userEvent.setup();
    renderWithClient(<LoginForm />);
    await fillLogin(user);
    const button = await screen.findByRole("button", { name: "Signing in…" });
    expect(button).toBeDisabled();
    await user.click(button);
    expect(calls.filter((c) => c.path === "/api/auth/login")).toHaveLength(1);
    release();
    await waitFor(() => expect(router.push).toHaveBeenCalled());
  });

  it("tells users whose session expired why they are here", () => {
    state.search = "expired=1";
    mockFetch({});
    renderWithClient(<LoginForm />);
    expect(screen.getByRole("status")).toHaveTextContent("Your session expired");
  });
});

describe("RegisterForm", () => {
  async function fill(user: ReturnType<typeof userEvent.setup>, password = "long enough pw", confirm = password) {
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), password);
    await user.type(screen.getByLabelText("Confirm password"), confirm);
    await user.click(screen.getByRole("button", { name: "Create account" }));
  }

  it("validates password length, bcrypt byte limit and confirmation", async () => {
    const { calls } = mockFetch({});
    const user = userEvent.setup();
    const { unmount } = renderWithClient(<RegisterForm />);
    await fill(user, "short", "different");
    expect(screen.getByText("Use at least 8 characters.")).toBeInTheDocument();
    expect(screen.getByText("The passwords do not match.")).toBeInTheDocument();
    unmount();

    renderWithClient(<RegisterForm />);
    await fill(user, "é".repeat(40));
    expect(screen.getByText(/at most 72 bytes/)).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("creates the account, signs in, and opens the notes page", async () => {
    const { to } = mockFetch({
      "POST /api/auth/register": { status: 201, json: { id: "u1", email: "new@example.com" } },
      "POST /api/auth/login": { json: {} },
    });
    const user = userEvent.setup();
    renderWithClient(<RegisterForm />);
    await fill(user);
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/notes"));
    expect(to("POST", "/api/auth/register")[0]?.body).toEqual({ email: "new@example.com", password: "long enough pw" });
    expect(to("POST", "/api/auth/login")).toHaveLength(1);
  });

  it("reports a duplicate email on the email field", async () => {
    mockFetch({ "POST /api/auth/register": { status: 409, json: { detail: "Email already registered" } } });
    const user = userEvent.setup();
    renderWithClient(<RegisterForm />);
    await fill(user);
    expect(await screen.findByText("An account with this email already exists.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(router.push).not.toHaveBeenCalled();
  });

  it("shows server-side validation messages", async () => {
    mockFetch({
      "POST /api/auth/register": {
        status: 400,
        json: { detail: "Invalid request", errors: [{ field: "email", message: "value is not a valid email address" }] },
      },
    });
    const user = userEvent.setup();
    renderWithClient(<RegisterForm />);
    await fill(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("value is not a valid email address");
  });
});

describe("AuthGate", () => {
  it("renders nothing private and redirects to sign-in when there is no session", async () => {
    mockFetch({
      "GET /api/auth/me": { status: 401, json: { detail: "Not authenticated" } },
      "POST /api/auth/refresh": { status: 401, json: { detail: "Authentication failed" } },
    });
    renderWithClient(
      <AuthGate>
        <p>secret page content</p>
      </AuthGate>,
    );
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login?next=%2Fnotes"));
    expect(screen.queryByText("secret page content")).not.toBeInTheDocument();
  });

  it("shows the app, the user, and navigation once signed in", async () => {
    mockFetch({ "GET /api/auth/me": { json: { id: "u1", email: "alice@example.com" } } });
    renderWithClient(
      <AuthGate>
        <p>my notes</p>
      </AuthGate>,
    );
    expect(await screen.findByText("my notes")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Notes" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Graph" })).not.toHaveAttribute("aria-current");
  });

  it("does not bounce users to sign-in when the server is merely unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
    renderWithClient(
      <AuthGate>
        <p>content</p>
      </AuthGate>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the server");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("sends the user to sign-in with a notice when the session expires mid-use", async () => {
    mockFetch({
      "GET /api/auth/me": { json: { id: "u1", email: "alice@example.com" } },
      "GET /api/tags": { status: 401, json: { detail: "Not authenticated" } },
      "POST /api/auth/refresh": { status: 401, json: {} },
    });
    const { api } = await import("@/lib/api");
    renderWithClient(
      <AuthGate>
        <p>content</p>
      </AuthGate>,
    );
    await screen.findByText("content");
    await api.listTags().catch(() => {});
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login?expired=1&next=%2Fnotes"));
  });

  it("signs out and returns to the login page", async () => {
    const { to } = mockFetch({
      "GET /api/auth/me": { json: { id: "u1", email: "alice@example.com" } },
      "POST /api/auth/logout": { status: 204 },
    });
    const user = userEvent.setup();
    renderWithClient(
      <AuthGate>
        <p>content</p>
      </AuthGate>,
    );
    await user.click(await screen.findByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(to("POST", "/api/auth/logout")).toHaveLength(1);
  });
});
