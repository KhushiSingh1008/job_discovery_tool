import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { routes } from "../app/routes";
import { HOURS_OK, jsonError, mockApi } from "../test/mockApi";
import { renderRoutes } from "../test/render";

const RESUME =
  "Sam Lee\n- Responsible for handling cash on the till\n- Served customers at weekends";
const JOB = "Weekend barista needing customer service, cash handling and food hygiene skills.";

function setup(enhance: () => unknown) {
  const api = mockApi({
    "GET /api/applications": () => [],
    "GET /api/applications/hours-summary": () => HOURS_OK,
    "POST /api/match": () => ({
      score: 64,
      summary: "Your resume shows 2 of the 3 skills this job mentions.",
      matched_skills: ["cash handling"],
      missing_skills: ["food hygiene"],
      suggestions: ["Use a number."],
      engine: "keyword",
      notice: null,
    }),
    "POST /api/resume/enhance": enhance,
  });
  renderRoutes(routes, "/match");
  return { ...api, user: userEvent.setup() };
}

describe("MatchPage", () => {
  it("scores a pasted job and lists edits to review", async () => {
    const { user, calls } = setup(() => ({
      engine: "rules",
      notice: null,
      suggestions: [
        {
          id: "s1",
          kind: "rewrite",
          section: "Experience",
          original: "Responsible for handling cash on the till",
          replacement: "Handled cash on the till",
          reason: "Opens with an action verb.",
        },
      ],
    }));

    const submit = screen.getByRole("button", { name: /Check my fit/ });
    expect(submit).toBeDisabled();
    await user.type(screen.getByLabelText("Your resume (plain text)"), RESUME);
    await user.type(screen.getByLabelText("Job description"), JOB);
    await user.click(submit);

    expect(await screen.findByText("food hygiene")).toBeInTheDocument();
    const card = screen.getByRole("group", { name: "Suggestion in Experience" });
    expect(within(card).getByText("Handled cash on the till")).toBeInTheDocument();
    // The match's generic bullet tips give way to the line-by-line edits.
    expect(screen.queryByText("Use a number.")).not.toBeInTheDocument();
    expect(calls.find((c) => c.url.pathname === "/api/resume/enhance")?.body).toEqual({
      resume_text: RESUME,
      job_description: JOB,
    });
  });

  it("says so when there is nothing to change", async () => {
    const { user } = setup(() => ({ engine: "rules", notice: null, suggestions: [] }));

    await user.type(screen.getByLabelText("Your resume (plain text)"), RESUME);
    await user.type(screen.getByLabelText("Job description"), JOB);
    await user.click(screen.getByRole("button", { name: /Check my fit/ }));

    expect(
      await screen.findByText("Your resume already reads well for this job"),
    ).toBeInTheDocument();
  });

  it("reports a failed analysis", async () => {
    const { user } = setup(() => jsonError(500, "Server error"));

    await user.type(screen.getByLabelText("Your resume (plain text)"), RESUME);
    await user.type(screen.getByLabelText("Job description"), JOB);
    await user.click(screen.getByRole("button", { name: /Check my fit/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't analyse your resume");
  });
});
