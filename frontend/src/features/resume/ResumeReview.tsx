import { useMemo, useState } from "react";

import type { EnhanceResult } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Tag } from "../../components/ui/Chip";
import { Icon } from "../../components/ui/Icon";
import { StateMessage } from "../../components/ui/States";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";
import {
  applySuggestions,
  countDecisions,
  type Decision,
  type Decisions,
} from "../../lib/resumeEdits";
import { SuggestionCard } from "./SuggestionCard";
import styles from "./Resume.module.css";

interface ResumeReviewProps {
  /** The exact resume text the suggestions were made for. */
  resume: string;
  result: EnhanceResult;
  onSaveResume: (text: string) => void;
}

function download(text: string, filename: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}

/** Accept or reject each suggestion and watch the tailored resume update beside it. */
export function ResumeReview({ resume, result, onSaveResume }: ResumeReviewProps) {
  const { suggestions } = result;
  const [decisions, setDecisions] = useState<Decisions>({});
  const [savedText, setSavedText] = useState<string | null>(null);
  const { copied, copy } = useCopyToClipboard();

  const edited = useMemo(
    () => applySuggestions(resume, suggestions, decisions),
    [resume, suggestions, decisions],
  );
  const counts = countDecisions(suggestions, decisions);
  const acceptedText = suggestions
    .filter((s) => decisions[s.id] === "accepted")
    .map((s) => s.replacement);

  const decide = (id: string, decision: Decision | undefined) =>
    setDecisions((current) => {
      const next: Record<string, Decision> = { ...current };
      if (decision) next[id] = decision;
      else delete next[id];
      return next;
    });
  const acceptAll = () =>
    setDecisions((current) =>
      Object.fromEntries(suggestions.map((s) => [s.id, current[s.id] ?? "accepted"])),
    );

  return (
    <div className={styles.review}>
      <section className={styles.reviewColumn} aria-labelledby="suggestions-heading">
        <div className={styles.reviewHead}>
          <div>
            <h3 id="suggestions-heading">Suggested changes</h3>
            <p className={styles.progress} aria-live="polite">
              {counts.accepted + counts.rejected} of {suggestions.length} reviewed
            </p>
          </div>
          <Tag tone={result.engine === "claude" ? "accent" : "neutral"}>
            {result.engine === "claude" ? "AI suggestions" : "Offline tips"}
          </Tag>
        </div>
        {result.notice && <p className={styles.notice}>{result.notice}</p>}

        {suggestions.length === 0 ? (
          <StateMessage title="Your resume already reads well for this job">
            No changes to suggest. Check the skills summary above for anything to add.
          </StateMessage>
        ) : (
          <>
            <ol className={styles.cards}>
              {suggestions.map((suggestion) => (
                <SuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  decision={decisions[suggestion.id]}
                  onDecide={(decision) => decide(suggestion.id, decision)}
                />
              ))}
            </ol>
            <div className={styles.bulk}>
              <Button size="sm" variant="secondary" disabled={!counts.pending} onClick={acceptAll}>
                Accept all remaining
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={counts.pending === suggestions.length}
                onClick={() => setDecisions({})}
              >
                Start over
              </Button>
            </div>
          </>
        )}
      </section>

      <section className={styles.previewColumn} aria-labelledby="preview-heading">
        <div className={styles.reviewHead}>
          <div>
            <h3 id="preview-heading">Your tailored resume</h3>
            <p className={styles.progress}>
              {counts.accepted} {counts.accepted === 1 ? "change" : "changes"} applied
            </p>
          </div>
        </div>
        <div className={styles.preview} tabIndex={0} aria-label="Resume preview">
          {edited.text.split("\n").map((line, index) => {
            const changed = line.trim() !== "" && acceptedText.some((t) => line.includes(t));
            return (
              <span key={index} className={changed ? styles.changedLine : undefined}>
                {line || " "}
              </span>
            );
          })}
        </div>
        {edited.skipped.length > 0 && (
          <p className={styles.notice}>
            {edited.skipped.length === 1
              ? "One accepted change could not be placed; edit it in by hand."
              : `${edited.skipped.length} accepted changes could not be placed; edit them in by hand.`}
          </p>
        )}
        <div className={styles.previewActions}>
          <Button size="sm" variant="secondary" onClick={() => void copy(edited.text)}>
            {copied ? "Copied" : "Copy text"}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => download(edited.text, "resume-tailored.txt")}
          >
            Download .txt
          </Button>
          <Button
            size="sm"
            variant="primary"
            disabled={counts.accepted === 0 || savedText === edited.text}
            onClick={() => {
              onSaveResume(edited.text);
              setSavedText(edited.text);
            }}
          >
            {savedText === edited.text ? (
              <>
                <Icon name="check" size={14} /> Saved as your resume
              </>
            ) : (
              "Use as my resume"
            )}
          </Button>
        </div>
      </section>
    </div>
  );
}
