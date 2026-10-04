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
  layoutSuggestions,
  type Decision,
  type Decisions,
} from "../../lib/resumeEdits";
import { ResumeDocument } from "./ResumeDocument";
import { SuggestionCard } from "./SuggestionCard";
import styles from "./Resume.module.css";

interface ResumeReviewProps {
  /** The exact resume text the suggestions were made for. */
  resume: string;
  result: EnhanceResult;
  onSaveResume: (text: string) => void;
}

const PREVIEW_CHARS = 48;

function download(text: string, filename: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}

function scrollToSuggestion(id: string) {
  document
    .querySelector(`[data-suggestion="${id}"]`) // ids are server-made: s1, s2…
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}

/**
 * Review suggestions where they apply: in the resume itself. Nothing changes until the
 * student accepts an edit, and every decision can be undone.
 */
export function ResumeReview({ resume, result, onSaveResume }: ResumeReviewProps) {
  const { suggestions } = result;
  const layout = useMemo(() => layoutSuggestions(resume, suggestions), [resume, suggestions]);
  const byId = useMemo(() => new Map(suggestions.map((s) => [s.id, s])), [suggestions]);

  // Document order: what the student meets reading top to bottom.
  const order = useMemo(
    () => [
      ...layout.top,
      ...layout.lines.flatMap((line) => [
        ...line.segments.flatMap((s) => (s.kind === "edit" ? [s.id] : [])),
        ...line.additions,
      ]),
    ],
    [layout],
  );

  const [decisions, setDecisions] = useState<Decisions>({});
  const [activeId, setActiveId] = useState<string | null>(order[0] ?? null);
  const [savedText, setSavedText] = useState<string | null>(null);
  const { copied, copy } = useCopyToClipboard();

  const edited = useMemo(
    () => applySuggestions(resume, suggestions, decisions),
    [resume, suggestions, decisions],
  );
  const counts = countDecisions(suggestions, decisions);
  const reviewed = counts.accepted + counts.rejected;

  const nextPending = (after: string | null, current: Decisions) => {
    const start = after ? order.indexOf(after) + 1 : 0;
    const rotated = [...order.slice(start), ...order.slice(0, start)];
    return rotated.find((id) => id !== after && !current[id]) ?? null;
  };

  const activate = (id: string) => setActiveId((current) => (current === id ? null : id));

  const decide = (id: string, decision: Decision | undefined) => {
    const next: Record<string, Decision> = { ...decisions };
    if (decision) next[id] = decision;
    else delete next[id];
    setDecisions(next);
    if (decision) {
      const following = nextPending(id, next);
      setActiveId(following);
      if (following) scrollToSuggestion(following);
    }
  };

  const goTo = (id: string) => {
    setActiveId(id);
    scrollToSuggestion(id);
  };

  if (suggestions.length === 0) {
    return (
      <StateMessage title="Your resume already reads well for this job">
        No changes to suggest. Check the skills summary above for anything to add.
      </StateMessage>
    );
  }

  const active = activeId ? byId.get(activeId) : undefined;
  const following = activeId ? nextPending(activeId, decisions) : null;
  const detail = active ? (
    <SuggestionCard
      key={active.id}
      suggestion={active}
      decision={decisions[active.id]}
      onDecide={(decision) => decide(active.id, decision)}
      onClose={() => setActiveId(null)}
      onNext={following ? () => goTo(following) : null}
    />
  ) : null;

  return (
    <div className={styles.review}>
      <section className={styles.documentColumn} aria-labelledby="document-heading">
        <div className={styles.reviewHead}>
          <div>
            <h3 id="document-heading">Your resume, with suggestions</h3>
            <p className={styles.progress}>
              Click a highlight to accept or reject it. Nothing changes until you accept.
            </p>
          </div>
        </div>
        <ResumeDocument
          layout={layout}
          suggestions={byId}
          decisions={decisions}
          activeId={activeId}
          onActivate={activate}
          detail={detail}
        />
      </section>

      <aside className={styles.sidebar} aria-label="Review progress">
        <div className={styles.reviewHead}>
          <div>
            <h3>Suggestions</h3>
            <p className={styles.progress} aria-live="polite">
              {reviewed} of {suggestions.length} reviewed
            </p>
          </div>
          <Tag tone={result.engine === "claude" ? "accent" : "neutral"}>
            {result.engine === "claude" ? "AI suggestions" : "Offline tips"}
          </Tag>
        </div>
        <div className={styles.progressBar} aria-hidden="true">
          <span style={{ width: `${(reviewed / suggestions.length) * 100}%` }} />
        </div>
        {result.notice && <p className={styles.notice}>{result.notice}</p>}

        <ul className={styles.legend} aria-label="Colour key">
          <li>
            <span className={`${styles.swatch} ${styles.swatchChange}`} /> Wording to change
          </li>
          <li>
            <span className={`${styles.swatch} ${styles.swatchNew}`} /> Suggested new words
          </li>
          <li>
            <span className={`${styles.swatch} ${styles.swatchAccepted}`} /> Accepted
          </li>
        </ul>

        <ol className={styles.outline}>
          {order.map((id) => {
            const edit = byId.get(id)!;
            const state = decisions[id] ?? "pending";
            const text =
              edit.replacement.length > PREVIEW_CHARS
                ? `${edit.replacement.slice(0, PREVIEW_CHARS)}…`
                : edit.replacement;
            return (
              <li key={id}>
                <button
                  type="button"
                  className={`${styles.outlineItem} ${activeId === id ? styles.outlineActive : ""}`}
                  onClick={() => goTo(id)}
                >
                  <span
                    className={`${styles.dot} ${styles[`dot_${state === "pending" ? edit.kind : state}`]}`}
                    aria-hidden="true"
                  />
                  <span>
                    <span className={styles.outlineSection}>{edit.section}</span>
                    <span className={styles.outlineText}>{text}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>

        <div className={styles.bulk}>
          <Button
            size="sm"
            variant="secondary"
            disabled={!counts.pending}
            onClick={() => {
              setDecisions(
                Object.fromEntries(suggestions.map((s) => [s.id, decisions[s.id] ?? "accepted"])),
              );
              setActiveId(null);
            }}
          >
            Accept all remaining
          </Button>
          <Button size="sm" variant="ghost" disabled={!reviewed} onClick={() => setDecisions({})}>
            Start over
          </Button>
        </div>

        {edited.skipped.length > 0 && (
          <p className={styles.notice}>
            {edited.skipped.length === 1
              ? "One accepted change could not be placed; edit it in by hand."
              : `${edited.skipped.length} accepted changes could not be placed; edit them in by hand.`}
          </p>
        )}

        <div className={styles.exportBox}>
          <p className={styles.exportTitle}>
            {counts.accepted} {counts.accepted === 1 ? "change" : "changes"} accepted
          </p>
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
          </div>
          <Button
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
      </aside>
    </div>
  );
}
