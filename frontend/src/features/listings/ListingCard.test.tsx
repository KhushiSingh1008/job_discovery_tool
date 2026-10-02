import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeListing } from "../../test/mockApi";
import { renderWithProviders } from "../../test/render";
import { ListingCard } from "./ListingCard";

describe("ListingCard", () => {
  it("shows the six required fields plus trust and visa fit", async () => {
    renderWithProviders(<ListingCard listing={makeListing()} />);

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
    expect(screen.getByText("via StudentJob UK")).toBeInTheDocument();
  });

  it("explains missing pay and low trust", async () => {
    renderWithProviders(
      <ListingCard listing={makeListing({ pay_hourly: null, pay_raw: null, trust_score: 25 })} />,
    );

    expect(await screen.findByText("Pay not stated")).toBeInTheDocument();
    expect(screen.getByText("Be careful")).toBeInTheDocument();
  });
});
