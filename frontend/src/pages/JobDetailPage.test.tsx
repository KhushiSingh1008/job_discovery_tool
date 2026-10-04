import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { routes } from "../app/routes";
import type { Application, EnhanceResult } from "../api/types";
import { HOURS_OK, jsonError, makeApplication, makeListing, mockApi } from "../test/mockApi";
import { renderRoutes } from "../test/render";

const LISTING = {
  ...makeListing({ trust_score: 25 }),
  description: "Serve great coffee.\n\nFlexible shifts around your studies.",
  first_seen: "2026-09-30T09:00:00Z",
  last_seen: "2026-10-02T09:00:00Z",
  trust_flags: [
    { code: "pay_disclosed", message: "Pay is stated clearly.", impact: 10 },
    { code: "scam_phrases", message: "Contains phrases common in job scams.", impact: -40 },
  ],
};

const RESUME =
  "Sam Lee\n- Responsible for handling cash on the till\n- Served customers at weekends";

const ENHANCED: EnhanceResult = {
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
    {
      id: "s2",
      kind: "add",
      section: "Profile",
      original: "Sam Lee",
      replacement: "Profile: student applying for the Weekend Barista role.",
      reason: "A short profile aimed at this role.",
    },
  ],
};

const MATCHED = {
  score: 64,
  summary: "Your resume shows 2 of the 3 skills this job mentions.",
  matched_skills: ["customer service", "cash handling"],
  missing_skills: ["food hygiene"],
  suggestions: [],
  engine: "keyword",
  notice: null,
};

function setup(applications: Application[] = [], createResponse?: () => unknown) {
  let current = applications;
  const api = mockApi({
    "GET /api/listings/barista-1": () => LISTING,
    "GET /api/applications": () => current,
    "GET /api/applications/hours-summary": () => HOURS_OK,
    "POST /api/applications": (_url, body) => {
      if (createResponse) return createResponse();
      const created = makeApplication(body as Partial<Application>);
      current = [created];
      return created;
    },
    "PATCH /api/applications/9": (_url, body) => {
      current = current.map((a) => ({ ...a, ...(body as Partial<Application>) }));
      return current[0];
    },
    "POST /api/resume/enhance": () => ENHANCED,
    "POST /api/match": () => MATCHED,
  });
  renderRoutes(routes, "/jobs/barista-1");
  return { ...api, user: userEvent.setup() };
}

describe("JobDetailPage", () => {
  it("explains the trust score, concerns first", async () => {
    setup();

    expect(await screen.findByRole("heading", { name: "Weekend Barista" })).toBeInTheDocument();
    const reasons = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(reasons[0]).toContain("Contains phrases common in job scams.");
    expect(screen.getByText("Flexible shifts around your studies.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Check my fit" })).toHaveAttribute(
      "href",
      "/match?listing=barista-1",
    );
  });

  it("links Apply now to the employer and offers to track the application", async () => {
    const { user, calls } = setup();

    const apply = await screen.findByRole("link", { name: /Apply now/ });
    expect(apply).toHaveAttribute("href", "https://example.com/barista");
    expect(apply).toHaveAttribute("target", "_blank");

    await user.click(apply);
    await user.click(await screen.findByRole("button", { name: "Yes, mark as applied" }));

    expect(await screen.findByText(/Tracked as applied/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      listing_id: "barista-1",
      status: "applied",
    });
  });

  it("moves a saved job to applied instead of adding it twice", async () => {
    const { user, calls } = setup([makeApplication({ status: "saved" })]);

    await user.click(await screen.findByRole("link", { name: /Apply now/ }));
    await user.click(await screen.findByRole("button", { name: "Yes, mark as applied" }));

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ status: "applied" }),
    );
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("shows tracker errors next to the follow-up", async () => {
    const { user } = setup([], () => jsonError(500, "Database is busy"));

    await user.click(await screen.findByRole("link", { name: /Apply now/ }));
    await user.click(await screen.findByRole("button", { name: "Yes, mark as applied" }));

    expect(await screen.findByText("Database is busy")).toBeInTheDocument();
  });

  it("enhances the resume: accept one edit, reject another, and keep the result", async () => {
    const { user, calls } = setup();

    await user.click(await screen.findByRole("button", { name: /Enhance my resume/ }));
    const drawer = await screen.findByRole("dialog", { name: "Enhance your resume" });

    await user.type(within(drawer).getByLabelText("Your resume (plain text)"), RESUME);
    await user.click(within(drawer).getByRole("button", { name: /Suggest improvements/ }));

    expect(await within(drawer).findByText("64")).toBeInTheDocument(); // fit score
    expect(calls.find((c) => c.url.pathname === "/api/resume/enhance")?.body).toEqual({
      resume_text: RESUME,
      listing_id: "barista-1",
    });

    // Suggestions are highlighted in the resume itself: yellow words to change, blue new words.
    const change = within(drawer).getByRole("button", { name: "Suggested change in Experience" });
    expect(change.querySelector("del")).toHaveTextContent("Responsible for handling");
    expect(change.querySelector("ins")).toHaveTextContent("Handled");

    // The first suggestion in reading order (the profile line) opens ready to review.
    const profileCard = within(drawer).getByRole("group", { name: "Suggestion in Profile" });
    await user.click(within(profileCard).getByRole("button", { name: /Reject/ }));

    // Deciding moves straight on to the next suggestion.
    const changeCard = await within(drawer).findByRole("group", {
      name: "Suggestion in Experience",
    });
    await user.click(within(changeCard).getByRole("button", { name: /Accept/ }));

    expect(
      within(drawer).getByRole("button", { name: "Accepted change in Experience" }),
    ).toHaveTextContent("Handled cash on the till");
    expect(
      within(drawer).getByRole("button", { name: "Rejected addition in Profile" }),
    ).toBeInTheDocument();
    expect(within(drawer).getByText("2 of 2 reviewed")).toBeInTheDocument();

    await user.click(within(drawer).getByRole("button", { name: "Use as my resume" }));
    const saved = JSON.parse(window.localStorage.getItem("gradguide.resume") ?? '""') as string;
    expect(saved).toBe("Sam Lee\n- Handled cash on the till\n- Served customers at weekends");
  });

  it("can undo a decision from the highlight", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: /Enhance my resume/ }));
    const drawer = await screen.findByRole("dialog");
    await user.type(within(drawer).getByLabelText("Your resume (plain text)"), RESUME);
    await user.click(within(drawer).getByRole("button", { name: /Suggest improvements/ }));

    const card = await within(drawer).findByRole("group", { name: "Suggestion in Profile" });
    await user.click(within(card).getByRole("button", { name: /Accept/ }));
    await user.click(within(drawer).getByRole("button", { name: "Accepted addition in Profile" }));
    const reopened = within(drawer).getByRole("group", { name: "Suggestion in Profile" });
    await user.click(within(reopened).getByRole("button", { name: "Undo" }));

    expect(
      within(drawer).getByRole("button", { name: "Suggested addition in Profile" }),
    ).toBeInTheDocument();
    expect(within(drawer).getByText("0 of 2 reviewed")).toBeInTheDocument();
  });

  it("closes the drawer with Escape", async () => {
    const { user } = setup();

    await user.click(await screen.findByRole("button", { name: /Enhance my resume/ }));
    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("handles a listing that has gone", async () => {
    mockApi({
      "GET /api/listings/gone": () => jsonError(404, "Listing not found"),
      "GET /api/applications": () => [],
      "GET /api/applications/hours-summary": () => HOURS_OK,
    });
    renderRoutes(routes, "/jobs/gone");

    expect(await screen.findByText("This job is no longer listed")).toBeInTheDocument();
  });
});
