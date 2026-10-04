import { useLocalStorage } from "./useLocalStorage";

/** The student's resume text, kept on this device only and shared by every resume tool. */
export function useSavedResume() {
  return useLocalStorage("gradguide.resume", "");
}

export const MIN_TEXT_LENGTH = 50;
