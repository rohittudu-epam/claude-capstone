import { describe, expect, it } from "vitest";

import { normalizeTag, safeNextPath } from "@/lib/utils";

describe("safeNextPath", () => {
  it.each(["/notes", "/notes/123", "/graph?x=1"])("allows %s", (path) => {
    expect(safeNextPath(path)).toBe(path);
  });

  it.each([null, undefined, "", "https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)", "notes"])(
    "falls back for %j",
    (path) => {
      expect(safeNextPath(path)).toBe("/notes");
    },
  );
});

describe("normalizeTag", () => {
  it("lowercases, trims and collapses whitespace like the server", () => {
    expect(normalizeTag("  Dev   Ops ")).toBe("dev ops");
    expect(normalizeTag("   ")).toBe("");
  });
});
