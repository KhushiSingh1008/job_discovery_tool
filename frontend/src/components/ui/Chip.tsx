import type { ReactNode } from "react";

import styles from "./Chip.module.css";

interface ToggleChipProps {
  pressed: boolean;
  onToggle: () => void;
  children: ReactNode;
  count?: number;
}

/** A pill-shaped toggle button (used for multi-select filters). */
export function ToggleChip({ pressed, onToggle, children, count }: ToggleChipProps) {
  return (
    <button type="button" className={styles.chip} aria-pressed={pressed} onClick={onToggle}>
      {children}
      {count !== undefined && <span className={styles.count}>{count}</span>}
    </button>
  );
}

export type TagTone = "neutral" | "accent" | "info" | "good" | "warn" | "bad" | "outline";

interface TagProps {
  tone?: TagTone;
  children: ReactNode;
  title?: string;
}

/** A small, non-interactive label. */
export function Tag({ tone = "neutral", children, title }: TagProps) {
  return (
    <span className={`${styles.tag} ${styles[tone]}`} title={title}>
      {children}
    </span>
  );
}
