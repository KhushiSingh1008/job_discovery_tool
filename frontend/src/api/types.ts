/** Mirrors of the backend's API schemas (backend/app/models.py and schemas.py). */

export const JOB_TYPES = ["part-time", "full-time", "internship"] as const;
export type JobType = (typeof JOB_TYPES)[number];

export const ELIGIBILITY_TAGS = [
  "student-friendly",
  "sponsorship-available",
  "right-to-work-required",
  "uk-citizens-only",
  "unknown",
] as const;
export type EligibilityTag = (typeof ELIGIBILITY_TAGS)[number];

export const APPLICATION_STATUSES = [
  "saved",
  "applied",
  "interviewing",
  "offered",
  "rejected",
] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

export const SORT_ORDERS = ["newest", "pay", "trust"] as const;
export type SortOrder = (typeof SORT_ORDERS)[number];

export interface TrustFlag {
  code: string;
  message: string;
  impact: number;
}

export interface ListingSummary {
  id: string;
  title: string;
  employer: string;
  location: string;
  pay_raw: string | null;
  pay_hourly: number | null;
  job_type: JobType;
  posted_date: string; // YYYY-MM-DD
  url: string;
  source: string;
  trust_score: number | null;
  eligibility_tag: EligibilityTag;
}

export interface Listing extends ListingSummary {
  description: string;
  first_seen: string;
  last_seen: string;
  trust_flags: TrustFlag[];
}

export interface ListingPage {
  items: ListingSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface FacetCount {
  value: string;
  count: number;
}

export interface FilterFacets {
  job_types: FacetCount[];
  sources: FacetCount[];
  locations: FacetCount[];
  eligibility: FacetCount[];
  max_pay_hourly: number | null;
}

export interface Application {
  id: number;
  listing_id: string;
  status: ApplicationStatus;
  weekly_hours: number;
  applied_at: string | null;
  last_contact_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  title: string;
  employer: string;
  location: string;
  url: string;
  job_type: JobType;
  pay_hourly: number | null;
}

export interface ApplicationCreate {
  listing_id: string;
  status?: ApplicationStatus;
  weekly_hours?: number;
  notes?: string;
}

export interface ApplicationUpdate {
  status?: ApplicationStatus;
  weekly_hours?: number;
  notes?: string;
  last_contact_at?: string;
}

export type HoursStatus = "ok" | "near_limit" | "over_limit" | "no_limit";

export interface HoursSummary {
  cap_hours: number | null;
  cap_source: "visa_rule" | "user_override" | "fallback";
  rule_label: string;
  vacation_note: string;
  source_url: string | null;
  committed_hours: number;
  potential_hours: number;
  remaining_hours: number | null;
  status: HoursStatus;
  message: string;
}

export interface Reminder {
  application_id: number;
  title: string;
  employer: string;
  status: ApplicationStatus;
  days_silent: number;
  draft_message: string;
}

export interface VisaRule {
  country: string;
  visa_type: string;
  label: string;
  hours_per_week: number | null;
  vacation_note: string;
  source_url: string;
}

export interface VisaRules {
  note: string;
  fallback_hours_per_week: number;
  rules: VisaRule[];
}

export interface MatchRequest {
  resume_text: string;
  listing_id?: string;
  job_description?: string;
}

export interface MatchResult {
  score: number;
  summary: string;
  matched_skills: string[];
  missing_skills: string[];
  suggestions: string[];
  engine: "claude" | "keyword";
  notice: string | null;
}

/** Query parameters accepted by GET /api/listings. */
export interface ListingQuery {
  q?: string;
  job_type?: JobType[];
  location?: string;
  min_pay?: number;
  min_trust?: number;
  eligibility?: EligibilityTag[];
  posted_within_days?: number;
  sort?: SortOrder;
  page?: number;
  page_size?: number;
}

export interface VisaSettings {
  country: string;
  visaType: string;
  capOverride: number | null;
}
