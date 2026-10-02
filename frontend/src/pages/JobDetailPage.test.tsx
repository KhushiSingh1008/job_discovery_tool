import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { routes } from "../app/routes";
import { HOURS_OK, jsonError, makeListing, mockApi } from "../test/mockApi";
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

function setup(trackResponse: () => unknown) {
  const api = mockApi({
    "GET /api/listings/barista-1": () => LISTING,
    "GET /api/applications/hours-summary": () => HOURS_OK,
    "POST /api/applications": trackResponse,
  });
  renderRoutes(routes, "/jobs/barista-1");
  return { ...api, user: userEvent.setup() };
}

describe("JobDetailPage", () => {
  it("explains the trust score, concerns first", async () => {
    setup(() => ({}));

    expect(await screen.findByRole("heading", { name: "Weekend Barista" })).toBeInTheDocument();
    const reasons = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(reasons[0]).toContain("Contains phrases common in job scams.");
    expect(screen.getByText("Flexible shifts around your studies.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Check my fit" })).toHaveAttribute(
      "href",
      "/match?listing=barista-1",
    );
  });

  it("tracks the job", async () => {
    const { user, calls } = setup(() => ({ id: 1 }));

    await user.click(await screen.findByRole("button", { name: "Track this job" }));

    expect(await screen.findByRole("link", { name: /Added. Open tracker/ })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ listing_id: "barista-1" });
  });

  it("treats an already-tracked job as success, not an error", async () => {
    const { user } = setup(() => jsonError(409, "This listing is already in your tracker"));

    await user.click(await screen.findByRole("button", { name: "Track this job" }));

    expect(
      await screen.findByRole("link", { name: /Already in your tracker/ }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("handles a listing that has gone", async () => {
    mockApi({
      "GET /api/listings/gone": () => jsonError(404, "Listing not found"),
      "GET /api/applications/hours-summary": () => HOURS_OK,
    });
    renderRoutes(routes, "/jobs/gone");

    expect(await screen.findByText("This job is no longer listed")).toBeInTheDocument();
  });
});
