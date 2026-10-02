import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { MatchResult } from "../../api/types";
import { MatchResultView } from "./MatchResultView";

const RESULT: MatchResult = {
  score: 72,
  summary: "Strong fit for the customer-facing parts of the role.",
  matched_skills: ["customer service", "cash handling"],
  missing_skills: ["food hygiene"],
  suggestions: ["Served [number] customers a day while handling cash accurately."],
  engine: "claude",
  notice: null,
};

describe("MatchResultView", () => {
  it("shows score, skills and suggestions", () => {
    render(<MatchResultView result={RESULT} />);

    expect(screen.getByRole("img", { name: "Match score 72 out of 100" })).toBeInTheDocument();
    expect(screen.getByText(RESULT.summary)).toBeInTheDocument();
    expect(screen.getByText("AI analysis")).toBeInTheDocument();
    expect(screen.getByText("customer service")).toBeInTheDocument();
    expect(screen.getByText("food hygiene")).toBeInTheDocument();
    expect(screen.getByText(RESULT.suggestions[0]!)).toBeInTheDocument();
  });

  it("copies a suggestion to the clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    render(<MatchResultView result={RESULT} />);

    await user.click(screen.getByRole("button", { name: "Copy" }));

    expect(writeText).toHaveBeenCalledWith(RESULT.suggestions[0]);
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("labels the offline engine and shows why it was used", () => {
    render(
      <MatchResultView
        result={{ ...RESULT, engine: "keyword", notice: "AI matching is unavailable." }}
      />,
    );

    expect(screen.getByText("Keyword match (offline)")).toBeInTheDocument();
    expect(screen.getByText("AI matching is unavailable.")).toBeInTheDocument();
  });
});
