import { useEnhance, useMatch } from "../../api/queries";
import type { MatchRequest } from "../../api/types";

/** Runs the fit score and the line-by-line suggestions for the same resume and job. */
export function useResumeAnalysis() {
  const match = useMatch();
  const enhance = useEnhance();

  return {
    match,
    enhance,
    isPending: match.isPending || enhance.isPending,
    run: (body: MatchRequest) => {
      match.mutate(body);
      enhance.mutate(body);
    },
  };
}

export type ResumeAnalysis = ReturnType<typeof useResumeAnalysis>;
