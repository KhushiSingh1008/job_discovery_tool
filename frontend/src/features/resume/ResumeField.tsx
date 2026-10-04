import { MIN_TEXT_LENGTH } from "../../hooks/useSavedResume";
import styles from "./Resume.module.css";

interface ResumeFieldProps {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
}

/** The resume textarea shared by the enhance drawer and the resume tools page. */
export function ResumeField({ value, onChange, rows = 12 }: ResumeFieldProps) {
  const ready = value.trim().length >= MIN_TEXT_LENGTH;
  return (
    <div className={styles.field}>
      <label htmlFor="resume">Your resume (plain text)</label>
      <textarea
        id="resume"
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Paste your resume. It stays on this device."
      />
      <span className={styles.hint}>
        {ready ? "Saved on this device" : `At least ${MIN_TEXT_LENGTH} characters`}
      </span>
    </div>
  );
}
