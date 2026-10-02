import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { FilterFacets, ListingQuery } from "../../api/types";
import { EMPTY_FACETS } from "../../test/mockApi";
import { FilterPanel } from "./FilterPanel";

const facets = EMPTY_FACETS as FilterFacets;

function setup(query: ListingQuery = {}) {
  const onChange = vi.fn();
  const onReset = vi.fn();
  render(<FilterPanel query={query} facets={facets} onChange={onChange} onReset={onReset} />);
  return { onChange, onReset, user: userEvent.setup() };
}

describe("FilterPanel", () => {
  it("toggles job types and shows facet counts", async () => {
    const { onChange, user } = setup({ job_type: ["full-time"] });

    const partTime = screen.getByRole("button", { name: /Part-time/ });
    expect(partTime).toHaveAttribute("aria-pressed", "false");
    expect(partTime).toHaveTextContent("3");
    expect(screen.getByRole("button", { name: /Full-time/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(partTime);
    expect(onChange).toHaveBeenCalledWith({ job_type: ["full-time", "part-time"] });
  });

  it("sets minimum pay, trust and recency", async () => {
    const { onChange, user } = setup();

    await user.selectOptions(screen.getByLabelText("Minimum hourly pay"), "12.71");
    expect(onChange).toHaveBeenLastCalledWith({ min_pay: 12.71 });

    await user.click(screen.getByRole("radio", { name: "Trusted (75+)" }));
    expect(onChange).toHaveBeenLastCalledWith({ min_trust: 75 });

    await user.click(screen.getByRole("radio", { name: "Past week" }));
    expect(onChange).toHaveBeenLastCalledWith({ posted_within_days: 7 });
  });

  it("picks a location from the facets", async () => {
    const { onChange, user } = setup();
    await user.selectOptions(screen.getByLabelText("Location"), "Manchester");
    expect(onChange).toHaveBeenCalledWith({ location: "Manchester" });
  });

  it("offers to clear only when filters are active", async () => {
    const { onReset, user } = setup({ job_type: ["part-time"], min_trust: 50 });

    await user.click(screen.getByRole("button", { name: "Clear 2" }));
    expect(onReset).toHaveBeenCalled();
  });

  it("hides the clear button with no filters", () => {
    setup();
    expect(screen.queryByRole("button", { name: /Clear/ })).not.toBeInTheDocument();
  });
});
