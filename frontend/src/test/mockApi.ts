import { vi } from "vitest";

import type { Application, ListingSummary } from "../api/types";

type Handler = (url: URL, body: unknown) => unknown;

export interface RecordedCall {
  method: string;
  url: URL;
  body: unknown;
}

/**
 * Stub ``fetch`` with handlers keyed by "METHOD /path". A handler may return a value
 * (sent as JSON 200) or a ``Response``. Unhandled requests fail loudly with 404.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const calls: RecordedCall[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const method = (init?.method ?? "GET").toUpperCase();
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
    calls.push({ method, url, body });

    const handler = handlers[`${method} ${url.pathname}`];
    if (!handler) {
      return new Response(JSON.stringify({ detail: `No mock for ${method} ${url.pathname}` }), {
        status: 404,
      });
    }
    const result = handler(url, body);
    if (result instanceof Response) return result;
    return new Response(result === undefined ? null : JSON.stringify(result), {
      status: result === undefined ? 204 : 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

export function jsonError(status: number, detail: string) {
  return new Response(JSON.stringify({ detail }), { status });
}

export function makeListing(overrides: Partial<ListingSummary> = {}): ListingSummary {
  return {
    id: "barista-1",
    title: "Weekend Barista",
    employer: "Bean & Leaf",
    location: "Manchester",
    pay_raw: "£12.80 per hour",
    pay_hourly: 12.8,
    job_type: "part-time",
    posted_date: "2026-09-30",
    url: "https://example.com/barista",
    source: "studentjob",
    trust_score: 82,
    eligibility_tag: "student-friendly",
    ...overrides,
  };
}

export function makeApplication(overrides: Partial<Application> = {}): Application {
  return {
    id: 9,
    listing_id: "barista-1",
    status: "saved",
    weekly_hours: 0,
    applied_at: null,
    last_contact_at: null,
    notes: "",
    created_at: "2026-09-20T10:00:00Z",
    updated_at: "2026-09-20T10:00:00Z",
    title: "Weekend Barista",
    employer: "Bean & Leaf",
    location: "Manchester",
    url: "https://example.com/barista",
    job_type: "part-time",
    pay_hourly: 12.8,
    ...overrides,
  };
}

export const EMPTY_FACETS = {
  job_types: [
    { value: "part-time", count: 3 },
    { value: "full-time", count: 2 },
    { value: "internship", count: 1 },
  ],
  sources: [{ value: "studentjob", count: 6 }],
  locations: [{ value: "Manchester", count: 2 }],
  eligibility: [{ value: "student-friendly", count: 1 }],
  max_pay_hourly: 25,
};

export const HOURS_OK = {
  cap_hours: 20,
  cap_source: "visa_rule",
  rule_label: "UK Student visa (degree level)",
  vacation_note: "Full-time work is allowed during official vacations.",
  source_url: "https://www.gov.uk/student-visa/work",
  committed_hours: 8,
  potential_hours: 8,
  remaining_hours: 12,
  status: "ok",
  message: "You have 12 of 20 hours a week left.",
};
