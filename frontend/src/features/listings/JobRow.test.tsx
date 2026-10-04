import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Application } from "../../api/types";
import { makeApplication, makeListing, mockApi } from "../../test/mockApi";
import { renderWithProviders } from "../../test/render";
import { JobRow } from "./JobRow";

function setup(applications: Application[] = []) {
  let current = applications;
  const api = mockApi({
    "GET /api/applications": () => current,
    "POST /api/applications": (_url, body) => {
      const created = makeApplication({ id: 9, ...(body as Partial<Application>) });
      current = [created];
      return created;
    },
    "DELETE /api/applications/9": () => {
      current = [];
      return undefined;
    },
  });
  return { ...api, user: userEvent.setup() };
}

describe("JobRow", () => {
  it("shows the six required fields plus trust and visa fit", async () => {
    setup();
    renderWithProviders(<JobRow listing={makeListing()} />);

    const title = await screen.findByRole("link", { name: "Weekend Barista" });
    expect(title).toHaveAttribute("href", "/jobs/barista-1");
    expect(screen.getByText("Bean & Leaf")).toBeInTheDocument(); // employer
    expect(screen.getByText("Manchester")).toBeInTheDocument(); // location
    expect(screen.getByText("£12.80/h")).toBeInTheDocument(); // pay
    expect(screen.getByText("Part-time")).toBeInTheDocument(); // job type
    expect(screen.getByText(/ago|Today|Yesterday|\d+ \w{3}/, { selector: "time" })).toHaveAttribute(
      "datetime",
      "2026-09-30",
    ); // posted date
    expect(screen.getByText("Trusted")).toBeInTheDocument();
    expect(screen.getByText("Student-friendly")).toBeInTheDocument();
  });

  it("links to the side pane when given a target and marks the selection", async () => {
    setup();
    renderWithProviders(<JobRow listing={makeListing()} to="?job=barista-1" selected />);

    const title = await screen.findByRole("link", { name: "Weekend Barista" });
    expect(title).toHaveAttribute("href", "/?job=barista-1");
    expect(title).toHaveAttribute("aria-current", "true");
  });

  it("explains missing pay and low trust", async () => {
    setup();
    renderWithProviders(
      <JobRow listing={makeListing({ pay_hourly: null, pay_raw: null, trust_score: 25 })} />,
    );

    expect(await screen.findByText("Pay not stated")).toBeInTheDocument();
    expect(screen.getByText("Be careful")).toBeInTheDocument();
  });

  it("saves and un-saves the job", async () => {
    const { user, calls } = setup();
    renderWithProviders(<JobRow listing={makeListing()} />);

    await user.click(await screen.findByRole("button", { name: "Save job" }));
    const saved = await screen.findByRole("button", { name: /Saved. Remove/ });
    expect(saved).toHaveAttribute("aria-pressed", "true");
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ listing_id: "barista-1" });

    await user.click(saved);
    expect(await screen.findByRole("button", { name: "Save job" })).toBeInTheDocument();
  });

  it("never removes an application that is in progress", async () => {
    setup([makeApplication({ status: "interviewing" })]);
    renderWithProviders(<JobRow listing={makeListing()} />);

    expect(
      await screen.findByRole("button", { name: "In your tracker: Interviewing" }),
    ).toBeDisabled();
  });
});
