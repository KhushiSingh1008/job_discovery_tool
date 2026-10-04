import { useState, type FormEvent } from "react";

import { Button } from "../../components/ui/Button";
import { Icon } from "../../components/ui/Icon";
import { MIN_TEXT_LENGTH, useSavedResume } from "../../hooks/useSavedResume";
import { AnalysisResults } from "./AnalysisResults";
import { ResumeField } from "./ResumeField";
import { useResumeAnalysis } from "./useResumeAnalysis";
import styles from "./Resume.module.css";

/** Drawer content: tailor the saved resume to one listing, edit by edit. */
export function EnhancePanel({ listingId }: { listingId: string }) {
  const [resume, setResume] = useSavedResume();
  const analysis = useResumeAnalysis();
  const [editing, setEditing] = useState(true);
  const ready = resume.trim().length >= MIN_TEXT_LENGTH;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    analysis.run({ resume_text: resume, listing_id: listingId });
    setEditing(false);
  };

  if (!editing) {
    return (
      <div className={styles.panel}>
        <div className={styles.panelBar}>
          <p>Suggestions are based on your saved resume. Nothing changes until you accept it.</p>
          <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
            Edit resume text
          </Button>
        </div>
        <AnalysisResults analysis={analysis} onSaveResume={setResume} />
      </div>
    );
  }

  return (
    <form className={styles.panel} onSubmit={submit}>
      <p className={styles.intro}>
        Paste your resume and we'll suggest edits that match this job's wording. You review each
        one: accept what's true for you, reject the rest.
      </p>
      <ResumeField value={resume} onChange={setResume} rows={14} />
      <div className={styles.submitRow}>
        <Button type="submit" variant="primary" size="lg" disabled={!ready}>
          <Icon name="sparkle" /> Suggest improvements
        </Button>
      </div>
    </form>
  );
}
