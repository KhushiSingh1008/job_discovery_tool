import type { VisaSettings } from "../api/types";
import { useLocalStorage } from "./useLocalStorage";

export const DEFAULT_VISA_SETTINGS: VisaSettings = {
  country: "UK",
  visaType: "student",
  capOverride: null,
};

/** The student's visa and optional personal hour limit, remembered on this device. */
export function useVisaSettings() {
  return useLocalStorage<VisaSettings>("gradguide.visa", DEFAULT_VISA_SETTINGS);
}
