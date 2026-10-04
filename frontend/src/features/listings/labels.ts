import type { EligibilityTag, SortOrder } from "../../api/types";
import type { TagTone } from "../../components/ui/Chip";

export const SOURCE_LABELS: Record<string, string> = {
  cambridge: "University of Cambridge",
  studentjob: "StudentJob UK",
  greenhouse: "Employer careers site",
};

export const ELIGIBILITY_TONES: Record<EligibilityTag, TagTone> = {
  "student-friendly": "good",
  "sponsorship-available": "info",
  "right-to-work-required": "neutral",
  "uk-citizens-only": "bad",
  "self-employed": "bad",
  unknown: "outline",
};

/** UK National Living Wage (21+) from April 2026, mirrored from backend/app/rules. */
export const LIVING_WAGE = 12.71;

export const SORT_LABELS: Record<SortOrder, string> = {
  newest: "Newest",
  pay: "Highest pay",
  trust: "Most trusted",
};
