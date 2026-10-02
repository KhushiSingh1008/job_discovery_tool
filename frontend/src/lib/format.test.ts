import { describe, expect, it } from "vitest";

import { formatHours, formatPay, formatPostedDate, trustLevel } from "./format";

describe("formatPay", () => {
  it("shows the hourly rate when known", () => {
    expect(formatPay(12.8, "£12.80 per hour")).toBe("£12.80/h");
  });

  it("falls back to the advertised text, then to a clear placeholder", () => {
    expect(formatPay(null, "Competitive")).toBe("Competitive");
    expect(formatPay(null, "  ")).toBe("Pay not stated");
    expect(formatPay(null, null)).toBe("Pay not stated");
  });
});

describe("formatPostedDate", () => {
  const today = new Date(2026, 9, 2); // 2 Oct 2026, local time

  it.each([
    ["2026-10-02", "Today"],
    ["2026-10-01", "Yesterday"],
    ["2026-09-28", "4 days ago"],
    ["2026-09-24", "1 week ago"],
    ["2026-09-10", "3 weeks ago"],
    ["2026-08-01", "1 Aug"],
    ["2026-10-05", "Today"], // future dates never read as "-3 days ago"
  ])("%s -> %s", (iso, expected) => {
    expect(formatPostedDate(iso, today)).toBe(expected);
  });
});

describe("trustLevel", () => {
  it.each([
    [90, "high"],
    [75, "high"],
    [74, "medium"],
    [50, "medium"],
    [49, "low"],
    [null, "unknown"],
  ] as const)("%s -> %s", (score, level) => {
    expect(trustLevel(score)).toBe(level);
  });
});

describe("formatHours", () => {
  it("keeps whole hours short and rounds fractions", () => {
    expect(formatHours(20)).toBe("20h");
    expect(formatHours(7.25)).toBe("7.3h");
  });
});
