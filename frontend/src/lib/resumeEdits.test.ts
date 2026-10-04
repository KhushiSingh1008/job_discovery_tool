import { describe, expect, it } from "vitest";

import type { ResumeSuggestion } from "../api/types";
import { applySuggestions, countDecisions } from "./resumeEdits";

const RESUME = ["Sam Lee", "", "- Responsible for the till", "- Served customers"].join("\n");

const edit = (id: string, overrides: Partial<ResumeSuggestion>): ResumeSuggestion => ({
  id,
  kind: "rewrite",
  section: "Experience",
  original: "",
  replacement: "",
  reason: "",
  ...overrides,
});

const SUGGESTIONS = [
  edit("s1", { kind: "add", original: "Sam Lee", replacement: "Profile: student" }),
  edit("s2", { original: "Responsible for the till", replacement: "Ran the till" }),
  edit("s3", { kind: "add", original: "Served customers", replacement: "- [Example]" }),
  edit("s4", { kind: "add", original: "", replacement: "TOP" }),
];

describe("applySuggestions", () => {
  it("leaves the resume unchanged until something is accepted", () => {
    expect(applySuggestions(RESUME, SUGGESTIONS, {}).text).toBe(RESUME);
    expect(applySuggestions(RESUME, SUGGESTIONS, { s1: "rejected" }).text).toBe(RESUME);
  });

  it("applies accepted rewrites and additions in place", () => {
    const { text, skipped } = applySuggestions(RESUME, SUGGESTIONS, {
      s1: "accepted",
      s2: "accepted",
      s3: "accepted",
      s4: "accepted",
    });

    expect(text.split("\n")).toEqual([
      "TOP",
      "Sam Lee",
      "Profile: student",
      "",
      "- Ran the till",
      "- Served customers",
      "- [Example]",
    ]);
    expect(skipped).toEqual([]);
  });

  it("anchors additions to the original text even when that line was rewritten", () => {
    const suggestions = [
      edit("a", { original: "Served customers", replacement: "Served 40 customers" }),
      edit("b", { kind: "add", original: "Served customers", replacement: "- New line" }),
    ];
    const { text } = applySuggestions(RESUME, suggestions, { a: "accepted", b: "accepted" });

    expect(text.split("\n").slice(-2)).toEqual(["- Served 40 customers", "- New line"]);
  });

  it("adds after the last line when the anchor has gone, and reports stale rewrites", () => {
    const suggestions = [
      edit("a", { kind: "add", original: "Not in resume", replacement: "- Extra" }),
      edit("b", { original: "Not in resume", replacement: "x" }),
    ];
    const { text, skipped } = applySuggestions(RESUME, suggestions, {
      a: "accepted",
      b: "accepted",
    });

    expect(text.endsWith("- Served customers\n- Extra")).toBe(true);
    expect(skipped).toEqual(["b"]);
  });

  it("treats $ patterns in replacements literally", () => {
    const suggestions = [edit("a", { original: "the till", replacement: "£$& takings" })];
    expect(applySuggestions(RESUME, suggestions, { a: "accepted" }).text).toContain(
      "Responsible for £$& takings",
    );
  });
});

describe("countDecisions", () => {
  it("counts accepted, rejected and pending", () => {
    expect(countDecisions(SUGGESTIONS, { s1: "accepted", s2: "rejected" })).toEqual({
      accepted: 1,
      rejected: 1,
      pending: 2,
    });
  });
});
