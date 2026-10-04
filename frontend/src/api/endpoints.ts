import { request, toQueryString } from "./client";
import type {
  Application,
  ApplicationCreate,
  ApplicationUpdate,
  EnhanceRequest,
  EnhanceResult,
  FilterFacets,
  HoursSummary,
  Listing,
  ListingPage,
  ListingQuery,
  ResumeText,
  SourceHealth,
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

  sources: () => request<SourceHealth[]>("/api/meta/sources"),

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

  /** The file goes as the raw body: the server reads it in memory and never stores it. */
  extractResume: (file: File) =>
    request<ResumeText>("/api/resume/extract", {
      method: "POST",
      body: file,
      headers: { "Content-Type": "application/octet-stream" },
    }),

  enhance: (data: EnhanceRequest) =>
    request<EnhanceResult>("/api/resume/enhance", { method: "POST", ...json(data) }),
};
