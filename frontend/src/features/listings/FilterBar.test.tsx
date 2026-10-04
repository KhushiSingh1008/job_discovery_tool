import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { FilterFacets, ListingQuery } from "../../api/types";
import { EMPTY_FACETS } from "../../test/mockApi";
import { FilterBar } from "./FilterBar";

const facets = EMPTY_FACETS as FilterFacets;

function setup(query: ListingQuery = {}) {
  const onChange = vi.fn();
  const onReset = vi.fn();
  render(<FilterBar query={query} facets={facets} onChange={onChange} onReset={onReset} />);
  return { onChange, onReset, user: userEvent.setup() };
}

describe("FilterBar", () => {
  it("opens a menu to toggle job types, with facet counts", async () => {
    const { onChange, user } = setup({ job_type: ["full-time"] });

    const pill = screen.getByRole("button", { name: /Full-time/ });
    expect(pill).toHaveAttribute("aria-expanded", "false");
    await user.click(pill);

    const partTime = screen.getByRole("button", { name: /Part-time/ });
    expect(partTime).toHaveAttribute("aria-pressed", "false");
    expect(partTime).toHaveTextContent("3");
    await user.click(partTime);
    expect(onChange).toHaveBeenCalledWith({ job_type: ["full-time", "part-time"] });
  });

  it("sets minimum pay, trust and recency", async () => {
    const { onChange, user } = setup();

    await user.click(screen.getByRole("button", { name: "Pay" }));
    await user.click(screen.getByRole("radio", { name: "£12.71/h+ (Living Wage)" }));
    expect(onChange).toHaveBeenLastCalledWith({ min_pay: 12.71 });

    await user.click(screen.getByRole("button", { name: "Trust score" }));
    await user.click(screen.getByRole("radio", { name: "Trusted (75+)" }));
    expect(onChange).toHaveBeenLastCalledWith({ min_trust: 75 });

    await user.click(screen.getByRole("button", { name: "Date posted" }));
    await user.click(screen.getByRole("radio", { name: "Past week" }));
    expect(onChange).toHaveBeenLastCalledWith({ posted_within_days: 7 });
  });

  it("summarises the chosen value on the pill", () => {
    setup({ min_pay: 15, eligibility: ["student-friendly", "sponsorship-available"] });

    expect(screen.getByRole("button", { name: "£15/h or more" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Visa fit · 2" })).toBeInTheDocument();
  });

  it("closes the menu with Escape and returns focus to the pill", async () => {
    const { user } = setup();
    const pill = screen.getByRole("button", { name: "Pay" });

    await user.click(pill);
    expect(screen.getByRole("group", { name: "Pay" })).toBeInTheDocument();
    await user.keyboard("{Escape}");

    expect(pill).toHaveAttribute("aria-expanded", "false");
    expect(pill).toHaveFocus();
  });

  it("changes the sort order", async () => {
    const { onChange, user } = setup();
    await user.selectOptions(screen.getByLabelText("Sort by"), "pay");
    expect(onChange).toHaveBeenCalledWith({ sort: "pay" });
  });

  it("offers to clear only when filters are active", async () => {
    const { onReset, user } = setup({ job_type: ["part-time"], min_trust: 50 });

    await user.click(screen.getByRole("button", { name: "Clear all (2)" }));
    expect(onReset).toHaveBeenCalled();
  });

  it("hides the clear button with no filters", () => {
    setup();
    expect(screen.queryByRole("button", { name: /Clear/ })).not.toBeInTheDocument();
  });
});
