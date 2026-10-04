import { motion } from "motion/react";

import type { ResumeSuggestion } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Icon } from "../../components/ui/Icon";
import type { Decision } from "../../lib/resumeEdits";
import styles from "./Resume.module.css";

interface SuggestionCardProps {
  suggestion: ResumeSuggestion;
  decision: Decision | undefined;
  onDecide: (decision: Decision | undefined) => void;
}

const ANCHOR_PREVIEW_CHARS = 60;

function shorten(text: string) {
  return text.length > ANCHOR_PREVIEW_CHARS ? `${text.slice(0, ANCHOR_PREVIEW_CHARS)}…` : text;
}

/** One proposed edit, shown as a before/after diff the student accepts or rejects. */
export function SuggestionCard({ suggestion, decision, onDecide }: SuggestionCardProps) {
  const { kind, section, original, replacement, reason } = suggestion;
  return (
    <motion.li
      layout
      className={`${styles.card} ${decision ? styles[decision] : ""}`}
      aria-label={`${kind === "add" ? "New line" : "Rewrite"} in ${section}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className={styles.cardHead}>
        <span className={styles.section}>{section}</span>
        <span className={styles.kind}>{kind === "add" ? "New line" : "Rewrite"}</span>
        {decision && (
          <span className={styles.status}>
            <Icon name={decision === "accepted" ? "check" : "close"} size={14} />
            {decision === "accepted" ? "Accepted" : "Rejected"}
          </span>
        )}
      </div>

      <div className={styles.diff}>
        {kind === "rewrite" ? (
          <del>
            <span className="visually-hidden">Replace: </span>
            {original}
          </del>
        ) : (
          original && <p className={styles.anchor}>After “{shorten(original)}”</p>
        )}
        <ins>
          <span className="visually-hidden">{kind === "rewrite" ? "With: " : "Add: "}</span>
          {replacement}
        </ins>
      </div>

      <p className={styles.reason}>
        <Icon name="sparkle" size={16} className={styles.reasonIcon} />
        {reason}
      </p>

      <div className={styles.cardActions}>
        {decision ? (
          <Button size="sm" variant="ghost" onClick={() => onDecide(undefined)}>
            Undo
          </Button>
        ) : (
          <>
            <Button size="sm" variant="primary" onClick={() => onDecide("accepted")}>
              <Icon name="check" size={14} /> Accept
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onDecide("rejected")}>
              <Icon name="close" size={14} /> Reject
            </Button>
          </>
        )}
      </div>
    </motion.li>
  );
}
