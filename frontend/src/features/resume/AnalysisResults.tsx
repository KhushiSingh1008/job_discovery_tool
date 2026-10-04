import { Skeleton, StateMessage } from "../../components/ui/States";
import { MatchResultView } from "../match/MatchResultView";
import { ResumeReview } from "./ResumeReview";
import type { ResumeAnalysis } from "./useResumeAnalysis";
import styles from "./Resume.module.css";

interface AnalysisResultsProps {
  analysis: ResumeAnalysis;
  onSaveResume: (text: string) => void;
}

function AnalysisSkeleton() {
  return (
    <div className={styles.loading} aria-busy="true" aria-label="Analysing your resume">
      <div className={styles.loadingHead}>
        <span className={styles.pulse} aria-hidden="true" />
        <p>Reading your resume against the job…</p>
      </div>
      <Skeleton height="5rem" />
      <Skeleton height="7rem" />
      <Skeleton height="7rem" width="85%" />
    </div>
  );
}

/** Fit score first, then the edits to accept or reject. */
export function AnalysisResults({ analysis, onSaveResume }: AnalysisResultsProps) {
  const { match, enhance, isPending } = analysis;

  if (isPending) return <AnalysisSkeleton />;
  if (match.isError || enhance.isError) {
    return (
      <StateMessage tone="error" title="We couldn't analyse your resume">
        {(match.error ?? enhance.error)?.message}
      </StateMessage>
    );
  }
  if (!match.data || !enhance.data || !enhance.variables) return null;

  return (
    <div className={styles.results}>
      <MatchResultView result={match.data} showSuggestions={false} />
      <ResumeReview
        // A new analysis starts a fresh review.
        key={enhance.submittedAt}
        resume={enhance.variables.resume_text}
        result={enhance.data}
        onSaveResume={onSaveResume}
      />
    </div>
  );
}
