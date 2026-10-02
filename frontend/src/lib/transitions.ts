import type { ApplicationStatus } from "../api/types";

/** Mirrors ALLOWED_TRANSITIONS in backend/app/services/tracker.py (the server enforces it). */
export const NEXT_STATUSES: Record<ApplicationStatus, readonly ApplicationStatus[]> = {
  saved: ["applied", "rejected"],
  applied: ["interviewing", "offered", "rejected"],
  interviewing: ["offered", "rejected"],
  offered: ["rejected"],
  rejected: [],
};

export const ACTION_LABELS: Record<ApplicationStatus, string> = {
  saved: "Save",
  applied: "Mark applied",
  interviewing: "Got interview",
  offered: "Got offer",
  rejected: "Close",
};
