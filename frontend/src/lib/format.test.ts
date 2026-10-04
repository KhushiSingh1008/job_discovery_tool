import { describe, expect, it } from "vitest";

import { formatHours, formatPay, formatPostedDate, formatRelativeTime, trustLevel } from "./format";

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

describe("formatRelativeTime", () => {
  const now = new Date("2026-10-04T12:00:00Z");
  it.each([
    ["2026-10-04T11:59:40Z", "just now"],
    ["2026-10-04T11:59:00Z", "1 minute ago"],
    ["2026-10-04T11:15:00Z", "45 minutes ago"],
    ["2026-10-04T09:00:00Z", "3 hours ago"],
    ["2026-10-02T12:00:00Z", "2 days ago"],
  ])("%s -> %s", (iso, expected) => {
    expect(formatRelativeTime(iso, now)).toBe(expected);
  });
});
