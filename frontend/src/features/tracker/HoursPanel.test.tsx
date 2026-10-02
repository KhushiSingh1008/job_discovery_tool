import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { HoursSummary } from "../../api/types";
import { HOURS_OK } from "../../test/mockApi";
import { HoursPanel } from "./HoursPanel";

const base = HOURS_OK as HoursSummary;

describe("HoursPanel", () => {
  it("shows hours used against the visa cap", () => {
    render(<HoursPanel summary={base} />);

    expect(screen.getByRole("heading", { name: "Within your limit" })).toBeInTheDocument();
    expect(screen.getByText("of 20h / week")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("You have 12 of 20 hours a week left.");
    expect(screen.getByRole("link", { name: /official rules/ })).toHaveAttribute(
      "href",
      "https://www.gov.uk/student-visa/work",
    );
  });

  it("warns clearly when over the limit", () => {
    render(
      <HoursPanel
        summary={{
          ...base,
          committed_hours: 24,
          potential_hours: 24,
          remaining_hours: -4,
          status: "over_limit",
          message: "Your jobs add up to 24 hours a week, over your 20-hour limit.",
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "Over your limit" })).toBeInTheDocument();
    expect(screen.getByText("Left this week").nextSibling).toHaveTextContent("0h");
  });

  it("handles visas without a weekly limit", () => {
    render(
      <HoursPanel
        summary={{ ...base, cap_hours: null, remaining_hours: null, status: "no_limit" }}
      />,
    );

    expect(screen.getByText("no limit")).toBeInTheDocument();
    expect(screen.queryByText("Left this week")).not.toBeInTheDocument();
  });
});
