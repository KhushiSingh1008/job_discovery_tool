import { describe, expect, it } from "vitest";

import {
  PAGE_SIZE,
  countActiveFilters,
  parseFilters,
  serializeFilters,
  toggleValue,
} from "./filters";

describe("parseFilters", () => {
  it("returns defaults for an empty URL", () => {
    expect(parseFilters(new URLSearchParams())).toEqual({
      q: undefined,
      job_type: [],
      location: undefined,
      min_pay: undefined,
      min_trust: undefined,
      eligibility: [],
      posted_within_days: undefined,
      sort: "newest",
      page: 1,
      page_size: PAGE_SIZE,
    });
  });

  it("reads repeated and numeric params", () => {
    const query = parseFilters(
      new URLSearchParams(
        "q=barista&job_type=part-time&job_type=internship&min_pay=12.71&sort=pay&page=3",
      ),
    );
    expect(query.q).toBe("barista");
    expect(query.job_type).toEqual(["part-time", "internship"]);
    expect(query.min_pay).toBe(12.71);
    expect(query.sort).toBe("pay");
    expect(query.page).toBe(3);
  });

  it("drops values the API would reject", () => {
    const query = parseFilters(
      new URLSearchParams("job_type=gig&eligibility=maybe&sort=random&page=-2&min_trust=abc"),
    );
    expect(query.job_type).toEqual([]);
    expect(query.eligibility).toEqual([]);
    expect(query.sort).toBe("newest");
    expect(query.page).toBe(1);
    expect(query.min_trust).toBeUndefined();
  });
});

describe("serializeFilters", () => {
  it("round-trips and omits defaults", () => {
    const params = new URLSearchParams(
      "q=tutor&job_type=part-time&eligibility=student-friendly&posted_within_days=7&page=2",
    );
    const roundTripped = serializeFilters(parseFilters(params));

    expect(roundTripped.toString()).toBe(params.toString());
    expect(serializeFilters(parseFilters(new URLSearchParams())).toString()).toBe("");
  });
});

describe("helpers", () => {
  it("counts active filters, excluding search and sort", () => {
    const query = parseFilters(
      new URLSearchParams("q=x&sort=pay&job_type=part-time&job_type=full-time&min_trust=75"),
    );
    expect(countActiveFilters(query)).toBe(3);
  });

  it("toggles values in a list", () => {
    expect(toggleValue(["a"], "b")).toEqual(["a", "b"]);
    expect(toggleValue(["a", "b"], "a")).toEqual(["b"]);
    expect(toggleValue(undefined, "a")).toEqual(["a"]);
  });
});
