import type { EligibilityTag } from "../../api/types";

export const SOURCE_LABELS: Record<string, string> = {
  cambridge: "University of Cambridge",
  studentjob: "StudentJob UK",
  greenhouse: "Employer careers site",
};

export const ELIGIBILITY_TONES: Record<
  EligibilityTag,
  "good" | "accent" | "neutral" | "bad" | "outline"
> = {
  "student-friendly": "good",
  "sponsorship-available": "accent",
  "right-to-work-required": "neutral",
  "uk-citizens-only": "bad",
  unknown: "outline",
};

/** UK National Living Wage (21+) from April 2026, mirrored from backend/app/rules. */
export const LIVING_WAGE = 12.71;
