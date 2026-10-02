import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { routes } from "../app/routes";
import type { Application } from "../api/types";
import { HOURS_OK, mockApi } from "../test/mockApi";
import { renderRoutes } from "../test/render";

const APPLICATION: Application = {
  id: 7,
  listing_id: "barista-1",
  status: "applied",
  weekly_hours: 12,
  applied_at: "2026-09-20T10:00:00Z",
  last_contact_at: "2026-09-20T10:00:00Z",
  notes: "",
  created_at: "2026-09-20T10:00:00Z",
  updated_at: "2026-09-20T10:00:00Z",
  title: "Weekend Barista",
  employer: "Bean & Leaf",
  location: "Manchester",
  url: "https://example.com/barista",
  job_type: "part-time",
  pay_hourly: 12.8,
};

const VISA_RULES = {
  note: "",
  fallback_hours_per_week: 20,
  rules: [
    {
      country: "UK",
      visa_type: "student",
      label: "UK Student visa (degree level)",
      hours_per_week: 20,
      vacation_note: "",
      source_url: "https://www.gov.uk/student-visa/work",
    },
    {
      country: "UK",
      visa_type: "graduate",
      label: "UK Graduate visa",
      hours_per_week: null,
      vacation_note: "",
      source_url: "https://www.gov.uk/graduate-visa",
    },
  ],
};

function setup(applications: Application[] = [APPLICATION]) {
  let current = applications;
  const api = mockApi({
    "GET /api/applications": () => current,
    "GET /api/applications/hours-summary": () => HOURS_OK,
    "GET /api/applications/reminders": () => [
      {
        application_id: 7,
        title: "Weekend Barista",
        employer: "Bean & Leaf",
        status: "applied",
        days_silent: 9,
        draft_message: "Subject: Following up on my application",
      },
    ],
    "GET /api/visa-rules": () => VISA_RULES,
    "PATCH /api/applications/7": (_url, body) => {
      current = current.map((a) => (a.id === 7 ? { ...a, ...(body as Partial<Application>) } : a));
      return current[0];
    },
  });
  renderRoutes(routes, "/tracker");
  return { ...api, user: userEvent.setup() };
}

describe("TrackerPage", () => {
  it("shows the hours guard, reminders and the pipeline", async () => {
    setup();

    expect(await screen.findByRole("heading", { name: "Within your limit" })).toBeInTheDocument();
    expect(await screen.findByText("9 days quiet")).toBeInTheDocument();
    const applied = await screen.findByRole("region", { name: /Applied/ });
    expect(within(applied).getByRole("link", { name: "Weekend Barista" })).toBeInTheDocument();
  });

  it("offers only the valid next steps and moves the card", async () => {
    const { user, calls } = setup();
    const applied = await screen.findByRole("region", { name: /Applied/ });

    expect(within(applied).queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    await user.click(within(applied).getByRole("button", { name: "Got interview" }));

    const interviewing = screen.getByRole("region", { name: /Interviewing/ });
    expect(
      await within(interviewing).findByRole("link", { name: "Weekend Barista" }),
    ).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ status: "interviewing" });
  });

  it("saves edited weekly hours on blur", async () => {
    const { user, calls } = setup();
    const input = await screen.findByLabelText("Hours/week");

    await user.clear(input);
    await user.type(input, "16");
    await user.tab();

    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ weekly_hours: 16 }),
    );
  });

  it("remembers the chosen visa and asks the API for its limit", async () => {
    const { user, calls } = setup();

    await screen.findByRole("option", { name: "UK Graduate visa" }); // rules loaded
    await user.selectOptions(screen.getByLabelText("Your visa"), "UK|graduate");

    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.url.pathname === "/api/applications/hours-summary" &&
            c.url.searchParams.get("visa_type") === "graduate",
        ),
      ).toBe(true),
    );
    expect(JSON.parse(window.localStorage.getItem("gradguide.visa") ?? "{}")).toMatchObject({
      visaType: "graduate",
    });
  });

  it("guides new users when nothing is tracked", async () => {
    setup([]);
    expect(await screen.findByText("Nothing tracked yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse jobs" })).toHaveAttribute("href", "/");
  });
});
