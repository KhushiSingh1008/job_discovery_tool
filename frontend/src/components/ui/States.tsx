import type { ReactNode } from "react";

import styles from "./States.module.css";

interface StateMessageProps {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  tone?: "neutral" | "error";
}

/** Empty and error states: say what happened and what to do next. */
export function StateMessage({ title, children, action, tone = "neutral" }: StateMessageProps) {
  return (
    <div className={`${styles.state} ${styles[tone]}`} role={tone === "error" ? "alert" : "status"}>
      <p className={styles.title}>{title}</p>
      {children && <p className={styles.body}>{children}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}

export function Skeleton({ height = "1rem", width = "100%" }: { height?: string; width?: string }) {
  return <span className={styles.skeleton} style={{ height, width }} aria-hidden="true" />;
}
