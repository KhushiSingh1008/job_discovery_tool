import type { ApplicationStatus, EligibilityTag, JobType } from "../api/types";

const DAY_MS = 24 * 60 * 60 * 1000;

export const JOB_TYPE_LABELS: Record<JobType, string> = {
  "part-time": "Part-time",
  "full-time": "Full-time",
  internship: "Internship",
};

export const ELIGIBILITY_LABELS: Record<EligibilityTag, string> = {
  "student-friendly": "Student-friendly",
  "sponsorship-available": "Visa sponsorship",
  "right-to-work-required": "Needs right to work",
  "uk-citizens-only": "UK citizens only",
  "self-employed": "Self-employed",
  unknown: "Visa fit unclear",
};

export const ELIGIBILITY_HINTS: Record<EligibilityTag, string> = {
  "student-friendly": "The advert welcomes students or offers hours around your studies.",
  "sponsorship-available": "The employer says it can sponsor a work visa.",
  "right-to-work-required":
    "You need existing right to work. A Student visa covers part-time work within your limit.",
  "uk-citizens-only": "Restricted to UK nationals or requires security clearance.",
  "self-employed":
    "Freelance or self-employed work. Not allowed on a Student visa, even within your hours.",
  unknown: "The advert does not mention visas. Ask the employer before you apply.",
};

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  interviewing: "Interviewing",
  offered: "Offered",
  rejected: "Closed",
};

const gbp = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" });

/** "£12.80/h" when the hourly rate is known, the page's own text otherwise. */
export function formatPay(payHourly: number | null, payRaw: string | null): string {
  if (payHourly !== null) return `${gbp.format(payHourly)}/h`;
  return payRaw?.trim() || "Pay not stated";
}

/** Parse YYYY-MM-DD as a local calendar date (not UTC midnight). */
function parseDate(isoDate: string): Date {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return new Date(year ?? 1970, (month ?? 1) - 1, day ?? 1);
}

export function formatPostedDate(isoDate: string, today: Date = new Date()): string {
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((startOfToday.getTime() - parseDate(isoDate).getTime()) / DAY_MS);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 14) return "1 week ago";
  if (days < 31) return `${Math.floor(days / 7)} weeks ago`;
  return parseDate(isoDate).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export type TrustLevel = "high" | "medium" | "low" | "unknown";

export function trustLevel(score: number | null): TrustLevel {
  if (score === null) return "unknown";
  if (score >= 75) return "high";
  if (score >= 50) return "medium";
  return "low";
}

export const TRUST_LABELS: Record<TrustLevel, string> = {
  high: "Trusted",
  medium: "Check details",
  low: "Be careful",
  unknown: "Not scored",
};

export function formatHours(hours: number): string {
  return `${Number.isInteger(hours) ? hours : hours.toFixed(1)}h`;
}

const MINUTE_MS = 60 * 1000;

/** "just now", "12 minutes ago", "3 hours ago", "2 days ago". */
export function formatRelativeTime(isoDateTime: string, now: Date = new Date()): string {
  const minutes = Math.round((now.getTime() - new Date(isoDateTime).getTime()) / MINUTE_MS);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
