/** Two-way mapping between the URL's search params and a typed listing query.
 *
 * Keeping filters in the URL makes searches shareable, bookmarkable and back-button safe.
 */
import {
  ELIGIBILITY_TAGS,
  JOB_TYPES,
  SORT_ORDERS,
  type EligibilityTag,
  type JobType,
  type ListingQuery,
  type SortOrder,
} from "../api/types";

export const PAGE_SIZE = 12;

function isOneOf<T extends string>(values: readonly T[], value: string): value is T {
  return (values as readonly string[]).includes(value);
}

function positiveNumber(value: string | null): number | undefined {
  if (value === null || value.trim() === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : undefined;
}

export function parseFilters(params: URLSearchParams): ListingQuery {
  const sort = params.get("sort") ?? "";
  const page = positiveNumber(params.get("page"));
  return {
    q: params.get("q")?.trim() || undefined,
    job_type: params.getAll("job_type").filter((v): v is JobType => isOneOf(JOB_TYPES, v)),
    location: params.get("location") || undefined,
    min_pay: positiveNumber(params.get("min_pay")),
    min_trust: positiveNumber(params.get("min_trust")),
    eligibility: params
      .getAll("eligibility")
      .filter((v): v is EligibilityTag => isOneOf(ELIGIBILITY_TAGS, v)),
    posted_within_days: positiveNumber(params.get("posted_within_days")),
    sort: isOneOf<SortOrder>(SORT_ORDERS, sort) ? sort : "newest",
    page: page ? Math.floor(page) : 1,
    page_size: PAGE_SIZE,
  };
}

/** Serialise back to search params, leaving defaults out to keep URLs short. */
export function serializeFilters(query: ListingQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  query.job_type?.forEach((type) => params.append("job_type", type));
  if (query.location) params.set("location", query.location);
  if (query.min_pay) params.set("min_pay", String(query.min_pay));
  if (query.min_trust) params.set("min_trust", String(query.min_trust));
  query.eligibility?.forEach((tag) => params.append("eligibility", tag));
  if (query.posted_within_days) params.set("posted_within_days", String(query.posted_within_days));
  if (query.sort && query.sort !== "newest") params.set("sort", query.sort);
  if (query.page && query.page > 1) params.set("page", String(query.page));
  return params;
}

export function countActiveFilters(query: ListingQuery): number {
  return (
    (query.job_type?.length ?? 0) +
    (query.eligibility?.length ?? 0) +
    [query.location, query.min_pay, query.min_trust, query.posted_within_days].filter(Boolean)
      .length
  );
}

export function toggleValue<T>(values: readonly T[] = [], value: T): T[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
}
