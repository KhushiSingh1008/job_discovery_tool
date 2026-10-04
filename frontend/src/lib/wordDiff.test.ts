import { describe, expect, it } from "vitest";

import { wordDiff } from "./wordDiff";

describe("wordDiff", () => {
  it("marks only the words that change", () => {
    expect(
      wordDiff(
        "Responsible for handling cash on the till",
        "Handled cash on the till, [add a number or result]",
      ),
    ).toEqual([
      { type: "removed", text: "Responsible for handling" },
      { type: "added", text: "Handled" },
      { type: "same", text: " cash on the till" },
      { type: "added", text: ", [add a number or result]" },
    ]);
  });

  it("returns one unchanged part for identical text", () => {
    expect(wordDiff("Served customers", "Served customers")).toEqual([
      { type: "same", text: "Served customers" },
    ]);
  });

  it("handles additions to and removals from empty text", () => {
    expect(wordDiff("", "New line")).toEqual([{ type: "added", text: "New line" }]);
    expect(wordDiff("Old line", "")).toEqual([{ type: "removed", text: "Old line" }]);
  });

  it("falls back to a whole replacement for very long text", () => {
    const before = "word ".repeat(300);
    const after = "other ".repeat(300);
    expect(wordDiff(before, after).map((part) => part.type)).toEqual(["removed", "added"]);
  });

  it("always rebuilds both texts exactly", () => {
    const before = "Worked on the weekly stock count with the team";
    const after = "Delivered the weekly stock count with a team of 4";
    const parts = wordDiff(before, after);
    const join = (keep: string) =>
      parts
        .filter((p) => p.type === "same" || p.type === keep)
        .map((p) => p.text)
        .join("");
    expect(join("removed")).toBe(before);
    expect(join("added")).toBe(after);
  });
});
