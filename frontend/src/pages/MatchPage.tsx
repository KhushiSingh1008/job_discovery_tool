import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";

import { useListing, useMatch } from "../api/queries";
import type { MatchRequest } from "../api/types";
import { Page } from "../components/layout/Page";
import { Button } from "../components/ui/Button";
import { StateMessage } from "../components/ui/States";
import { MatchResultView } from "../features/match/MatchResultView";
import { useLocalStorage } from "../hooks/useLocalStorage";
import styles from "../features/match/Match.module.css";

export const MIN_TEXT_LENGTH = 50;

function SelectedListing({ id, onClear }: { id: string; onClear: () => void }) {
  const { data, isPending, isError } = useListing(id);
  return (
    <div className={styles.selected}>
      <p className={styles.selectedLabel}>Matching against</p>
      {isPending ? (
        <p>Loading job…</p>
      ) : isError ? (
        <p>That job could not be found.</p>
      ) : (
        <p>
          <Link to={`/jobs/${data.id}`}>
            <strong>{data.title}</strong>
          </Link>{" "}
          at {data.employer}
        </p>
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
  const [resume, setResume] = useLocalStorage("gradguide.resume", "");
  const [jobText, setJobText] = useState("");
  const match = useMatch();

  const resumeReady = resume.trim().length >= MIN_TEXT_LENGTH;
  const jobReady = listingId !== null || jobText.trim().length >= MIN_TEXT_LENGTH;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!resumeReady || !jobReady) return;
    const body: MatchRequest = listingId
      ? { resume_text: resume, listing_id: listingId }
      : { resume_text: resume, job_description: jobText };
    match.mutate(body);
  };

  return (
    <Page title="Resume match">
      <header className={styles.header}>
        <h1>Check your fit before you apply</h1>
        <p className={styles.lead}>
          Paste your resume and a job. You'll see which requirements you already meet, what's
          missing, and how to word your real experience for this role.
        </p>
      </header>

      <form className={styles.form} onSubmit={submit}>
        <div className={styles.field}>
          <label htmlFor="resume">Your resume (plain text)</label>
          <textarea
            id="resume"
            rows={12}
            value={resume}
            onChange={(event) => setResume(event.target.value)}
            placeholder="Paste your resume. It is kept on this device only."
          />
          <span className={styles.hint}>
            {resumeReady ? "Saved on this device" : `At least ${MIN_TEXT_LENGTH} characters`}
          </span>
        </div>

        <div className={styles.field}>
          {listingId ? (
            <SelectedListing id={listingId} onClear={() => setParams({})} />
          ) : (
            <>
              <label htmlFor="job">Job description</label>
              <textarea
                id="job"
                rows={12}
                value={jobText}
                onChange={(event) => setJobText(event.target.value)}
                placeholder="Paste the advert, or open a job and choose “Check my fit”."
              />
              <span className={styles.hint}>
                {jobReady ? "Ready" : `At least ${MIN_TEXT_LENGTH} characters`}
              </span>
            </>
          )}
        </div>

        <div className={styles.submit}>
          <Button
            type="submit"
            variant="primary"
            disabled={!resumeReady || !jobReady || match.isPending}
          >
            {match.isPending ? "Analysing…" : "Check my fit"}
          </Button>
        </div>
      </form>

      {match.isError && (
        <StateMessage tone="error" title="The match could not be run">
          {match.error.message}
        </StateMessage>
      )}
      {match.data && <MatchResultView result={match.data} />}
    </Page>
  );
}
