import type { CSSProperties } from "react";

import { TRUST_LABELS, trustLevel } from "../../lib/format";
import styles from "./TrustBadge.module.css";

interface TrustBadgeProps {
  score: number | null;
  size?: "sm" | "lg";
}

/** A ring that fills with the trust score, coloured by level. */
export function TrustBadge({ score, size = "sm" }: TrustBadgeProps) {
  const level = trustLevel(score);
  const label = TRUST_LABELS[level];
  return (
    <span
      className={`${styles.badge} ${styles[level]} ${styles[size]}`}
      title={`Trust score: ${score ?? "n/a"} / 100 (${label})`}
    >
      <span
        className={styles.ring}
        style={{ "--fill": `${score ?? 0}%` } as CSSProperties}
        aria-hidden="true"
      >
        <span className={styles.score}>{score ?? "–"}</span>
      </span>
      <span className={styles.label}>
        <span className="visually-hidden">Trust score {score ?? "not available"}: </span>
        {label}
      </span>
    </span>
  );
}
