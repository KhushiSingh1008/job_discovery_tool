import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";

import { useListing } from "../api/queries";
import type { MatchRequest } from "../api/types";
import { Page } from "../components/layout/Page";
import { Avatar } from "../components/ui/Avatar";
import { Button } from "../components/ui/Button";
import { Icon } from "../components/ui/Icon";
import { AnalysisResults } from "../features/resume/AnalysisResults";
import { ResumeField } from "../features/resume/ResumeField";
import { useResumeAnalysis } from "../features/resume/useResumeAnalysis";
import { MIN_TEXT_LENGTH, useSavedResume } from "../hooks/useSavedResume";
import resumeStyles from "../features/resume/Resume.module.css";
import styles from "./MatchPage.module.css";

function SelectedListing({ id, onClear }: { id: string; onClear: () => void }) {
  const { data, isPending, isError } = useListing(id);
  return (
    <div className={styles.selected}>
      <p className={styles.selectedLabel}>Tailoring for</p>
      {isPending ? (
        <p>Loading job…</p>
      ) : isError ? (
        <p>That job could not be found.</p>
      ) : (
        <div className={styles.selectedJob}>
          <Avatar name={data.employer} />
          <p>
            <Link to={`/jobs/${data.id}`}>
              <strong>{data.title}</strong>
            </Link>
            <br />
            {data.employer}
          </p>
        </div>
      )}
      <Button size="sm" variant="ghost" onClick={onClear}>
        Paste a job description instead
      </Button>
    </div>
  );
}

export function MatchPage() {
  const [params, setParams] = useSearchParams();
  const listingId = params.get("listing");
  const [resume, setResume] = useSavedResume();
  const [jobText, setJobText] = useState("");
  const analysis = useResumeAnalysis();

  const resumeReady = resume.trim().length >= MIN_TEXT_LENGTH;
  const jobReady = listingId !== null || jobText.trim().length >= MIN_TEXT_LENGTH;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!resumeReady || !jobReady) return;
    const body: MatchRequest = listingId
      ? { resume_text: resume, listing_id: listingId }
      : { resume_text: resume, job_description: jobText };
    analysis.run(body);
  };

  return (
    <Page title="Resume tools">
      <header className={styles.header}>
        <p className={styles.eyebrow}>Resume tools</p>
        <h1>Tailor your resume to a job</h1>
        <p className={styles.lead}>
          See how well you fit, then review suggested edits one by one. Accept what's true for you,
          reject the rest, and take away a resume written in the employer's language.
        </p>
      </header>

      <form className={styles.form} onSubmit={submit}>
        <ResumeField value={resume} onChange={setResume} />

        {listingId ? (
          <SelectedListing id={listingId} onClear={() => setParams({})} />
        ) : (
          <div className={resumeStyles.field}>
            <label htmlFor="job">Job description</label>
            <textarea
              id="job"
              rows={12}
              value={jobText}
              onChange={(event) => setJobText(event.target.value)}
              placeholder="Paste the advert, or open a job and choose “Check my fit”."
            />
            <span className={resumeStyles.hint}>
              {jobReady ? "Ready" : `At least ${MIN_TEXT_LENGTH} characters`}
            </span>
          </div>
        )}

        <div className={styles.submit}>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            disabled={!resumeReady || !jobReady || analysis.isPending}
          >
            <Icon name="sparkle" />
            {analysis.isPending ? "Analysing…" : "Check my fit"}
          </Button>
        </div>
      </form>

      <AnalysisResults analysis={analysis} onSaveResume={setResume} />
    </Page>
  );
}
