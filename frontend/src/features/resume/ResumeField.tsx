import { useRef, useState, type DragEvent } from "react";

import { useExtractResume } from "../../api/queries";
import { Button } from "../../components/ui/Button";
import { Icon } from "../../components/ui/Icon";
import { MIN_TEXT_LENGTH } from "../../hooks/useSavedResume";
import styles from "./Resume.module.css";

interface ResumeFieldProps {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
}

const MAX_FILE_BYTES = 2 * 1024 * 1024;
const ACCEPTED = /\.(pdf|docx|txt)$/i;
const ACCEPT_ATTRIBUTE =
  ".pdf,.docx,.txt,application/pdf,text/plain," +
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/**
 * Upload a resume file or paste its text. Uploads are checked here for a quick answer,
 * then read by the server in memory; only the extracted text is kept, on this device.
 */
export function ResumeField({ value, onChange, rows = 12 }: ResumeFieldProps) {
  const extract = useExtractResume();
  const picker = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const ready = value.trim().length >= MIN_TEXT_LENGTH;
  const error = fileError ?? (extract.isError ? extract.error.message : null);

  const readFile = (file: File) => {
    extract.reset();
    setFileName(file.name);
    setFileError(null);
    if (!ACCEPTED.test(file.name)) {
      setFileError("Upload a PDF, Word (.docx) or .txt file.");
    } else if (file.size > MAX_FILE_BYTES) {
      setFileError("Files must be 2 MB or smaller.");
    } else {
      extract.mutate(file, { onSuccess: ({ text }) => onChange(text) });
    }
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) readFile(file);
  };

  return (
    <div className={styles.field}>
      <label htmlFor="resume">Your resume (plain text)</label>

      <div
        className={`${styles.upload} ${dragging ? styles.dragging : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <span className={styles.uploadIcon} aria-hidden="true">
          <Icon name="upload" size={20} />
        </span>
        <div className={styles.uploadText}>
          <p>
            <strong>Upload your resume</strong> or drop it here
          </p>
          <p className={styles.hint}>
            PDF, Word (.docx) or .txt, up to 2 MB. Read once for its text and never stored.
          </p>
        </div>
        <Button
          size="sm"
          variant="secondary"
          disabled={extract.isPending}
          onClick={() => picker.current?.click()}
        >
          {extract.isPending ? "Reading…" : "Choose file"}
        </Button>
        <input
          ref={picker}
          type="file"
          accept={ACCEPT_ATTRIBUTE}
          className="visually-hidden"
          aria-label="Upload resume file"
          tabIndex={-1}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) readFile(file);
            event.target.value = ""; // choosing the same file again still triggers a read
          }}
        />
      </div>

      {error ? (
        <p className={styles.fileError} role="alert">
          {fileName ? `${fileName}: ` : ""}
          {error}
        </p>
      ) : (
        extract.isSuccess &&
        fileName && (
          <p className={styles.fileOk} role="status">
            <Icon name="file" size={16} /> Text loaded from {fileName}. Check it below before you
            continue.
          </p>
        )
      )}

      <p className={styles.divider} aria-hidden="true">
        <span>or paste the text</span>
      </p>

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
