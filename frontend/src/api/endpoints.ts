import { request, toQueryString } from "./client";
import type {
  Application,
  ApplicationCreate,
  ApplicationUpdate,
  FilterFacets,
  HoursSummary,
  Listing,
  ListingPage,
  ListingQuery,
  MatchRequest,
  MatchResult,
  Reminder,
  VisaRules,
  VisaSettings,
} from "./types";

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const api = {
  listings: (query: ListingQuery) =>
    request<ListingPage>(`/api/listings${toQueryString({ ...query })}`),

  listing: (id: string) => request<Listing>(`/api/listings/${encodeURIComponent(id)}`),

  facets: () => request<FilterFacets>("/api/meta/filters"),

  visaRules: () => request<VisaRules>("/api/visa-rules"),

  applications: () => request<Application[]>("/api/applications"),

  createApplication: (data: ApplicationCreate) =>
    request<Application>("/api/applications", { method: "POST", ...json(data) }),

  updateApplication: (id: number, data: ApplicationUpdate) =>
    request<Application>(`/api/applications/${id}`, { method: "PATCH", ...json(data) }),

  deleteApplication: (id: number) => request<void>(`/api/applications/${id}`, { method: "DELETE" }),

  hoursSummary: ({ country, visaType, capOverride }: VisaSettings) =>
    request<HoursSummary>(
      `/api/applications/hours-summary${toQueryString({
        country,
        visa_type: visaType,
        cap_override: capOverride,
      })}`,
    ),

  reminders: () => request<Reminder[]>("/api/applications/reminders"),

  match: (data: MatchRequest) =>
    request<MatchResult>("/api/match", { method: "POST", ...json(data) }),
};
