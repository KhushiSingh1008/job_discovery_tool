import { Fragment, type KeyboardEvent, type ReactNode } from "react";

import type { ResumeSuggestion } from "../../api/types";
import { Icon } from "../../components/ui/Icon";
import type { Decision, Decisions, ResumeLayout } from "../../lib/resumeEdits";
import { wordDiff } from "../../lib/wordDiff";
import styles from "./Resume.module.css";

interface ResumeDocumentProps {
  layout: ResumeLayout;
  suggestions: ReadonlyMap<string, ResumeSuggestion>;
  decisions: Decisions;
  activeId: string | null;
  onActivate: (id: string) => void;
  /** The accept/reject card, shown under the line holding the active suggestion. */
  detail: ReactNode;
}

const STATE_WORDS: Record<Decision | "pending", string> = {
  pending: "Suggested",
  accepted: "Accepted",
  rejected: "Rejected",
};

/** Clickable inline text. A <span> (not a <button>) so long suggestions wrap like prose. */
function Clickable({
  id,
  label,
  active,
  className,
  onActivate,
  children,
  block = false,
}: {
  id: string;
  label: string;
  active: boolean;
  className: string;
  onActivate: (id: string) => void;
  children: ReactNode;
  block?: boolean;
}) {
  const Tag = block ? "div" : "span";
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    onActivate(id);
  };
  return (
    <Tag
      role="button"
      tabIndex={0}
      aria-label={label}
      aria-expanded={active}
      data-suggestion={id}
      className={`${className} ${active ? styles.active : ""}`}
      onClick={() => onActivate(id)}
      onKeyDown={onKeyDown}
    >
      {children}
    </Tag>
  );
}

/**
 * The resume as a page, with each suggestion shown in place: words to change in yellow,
 * suggested new words in blue, accepted edits in green.
 */
export function ResumeDocument({
  layout,
  suggestions,
  decisions,
  activeId,
  onActivate,
  detail,
}: ResumeDocumentProps) {
  const state = (id: string) => decisions[id] ?? "pending";
  const label = (edit: ResumeSuggestion) =>
    `${STATE_WORDS[state(edit.id)]} ${edit.kind === "add" ? "addition" : "change"} in ${edit.section}`;

  const renderAddition = (id: string) => {
    const edit = suggestions.get(id)!;
    const current = state(id);
    return (
      <Fragment key={id}>
        <Clickable
          id={id}
          block
          label={label(edit)}
          active={activeId === id}
          className={`${styles.addition} ${styles[current]}`}
          onActivate={onActivate}
        >
          {current === "pending" && <Icon name="plus" size={14} className={styles.additionIcon} />}
          {edit.replacement}
        </Clickable>
        {activeId === id && detail}
      </Fragment>
    );
  };

  const renderRewrite = (id: string) => {
    const edit = suggestions.get(id)!;
    const current = state(id);
    return (
      <Clickable
        key={id}
        id={id}
        label={label(edit)}
        active={activeId === id}
        className={`${styles.mark} ${styles[current]}`}
        onActivate={onActivate}
      >
        {current === "pending"
          ? wordDiff(edit.original, edit.replacement).map((part, index) =>
              part.type === "same" ? (
                <span key={index}>{part.text}</span>
              ) : part.type === "removed" ? (
                <del key={index} className={styles.change}>
                  {part.text}
                </del>
              ) : (
                <ins key={index} className={styles.insert}>
                  {part.text}
                </ins>
              ),
            )
          : current === "accepted"
            ? edit.replacement
            : edit.original}
      </Clickable>
    );
  };

  return (
    <div className={styles.paper} aria-label="Your resume with suggested changes">
      {layout.top.map(renderAddition)}
      {layout.lines.map((line, index) => {
        const holdsActive = line.segments.some((s) => s.kind === "edit" && s.id === activeId);
        const empty = line.segments.every((s) => s.kind === "text" && !s.text.trim());
        return (
          <Fragment key={index}>
            <p className={empty ? styles.blankLine : styles.line}>
              {line.segments.map((segment, i) =>
                segment.kind === "text" ? (
                  <Fragment key={i}>{segment.text}</Fragment>
                ) : (
                  renderRewrite(segment.id)
                ),
              )}
            </p>
            {holdsActive && detail}
            {line.additions.map(renderAddition)}
          </Fragment>
        );
      })}
    </div>
  );
}
