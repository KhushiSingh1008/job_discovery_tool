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
  onClose: () => void;
  onNext: (() => void) | null;
}

/** The accept/reject card that opens under a highlighted suggestion. */
export function SuggestionCard({
  suggestion,
  decision,
  onDecide,
  onClose,
  onNext,
}: SuggestionCardProps) {
  const { kind, section, original, replacement, reason } = suggestion;
  return (
    <motion.div
      className={`${styles.card} ${decision ? styles[decision] : ""}`}
      role="group"
      aria-label={`Suggestion in ${section}`}
      initial={{ opacity: 0, y: -4, height: 0 }}
      animate={{ opacity: 1, y: 0, height: "auto" }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className={styles.cardHead}>
        <span className={styles.section}>{section}</span>
        <span className={styles.kind}>{kind === "add" ? "New text" : "Change wording"}</span>
        {decision && (
          <span className={styles.status}>
            <Icon name={decision === "accepted" ? "check" : "close"} size={14} />
            {decision === "accepted" ? "Accepted" : "Rejected"}
          </span>
        )}
        <button type="button" className={styles.cardClose} aria-label="Close" onClick={onClose}>
          <Icon name="close" size={14} />
        </button>
      </div>

      {kind === "rewrite" ? (
        <p className={styles.compare}>
          <del className={styles.change}>{original}</del>
          <Icon name="arrowRight" size={14} className={styles.compareArrow} />
          <ins className={styles.insert}>{replacement}</ins>
        </p>
      ) : (
        <p className={styles.compare}>
          <ins className={styles.insert}>{replacement}</ins>
        </p>
      )}

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
        {onNext && (
          <Button size="sm" variant="ghost" className={styles.next} onClick={onNext}>
            Next suggestion <Icon name="arrowRight" size={14} />
          </Button>
        )}
      </div>
    </motion.div>
  );
}
