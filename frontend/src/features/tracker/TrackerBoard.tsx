import { AnimatePresence, LayoutGroup } from "motion/react";

import { APPLICATION_STATUSES, type Application } from "../../api/types";
import { STATUS_LABELS } from "../../lib/format";
import { ApplicationCard } from "./ApplicationCard";
import styles from "./Tracker.module.css";

/** Status columns; cards glide between columns when their status changes. */
export function TrackerBoard({ applications }: { applications: Application[] }) {
  return (
    <LayoutGroup>
      <div className={styles.board}>
        {APPLICATION_STATUSES.map((status) => {
          const items = applications.filter((application) => application.status === status);
          return (
            <section key={status} className={styles.column} aria-labelledby={`col-${status}`}>
              <h3 id={`col-${status}`} className={styles.columnTitle}>
                {STATUS_LABELS[status]}
                <span className={styles.columnCount}>{items.length}</span>
              </h3>
              <ul className={styles.columnList}>
                <AnimatePresence initial={false}>
                  {items.map((application) => (
                    <ApplicationCard key={application.id} application={application} />
                  ))}
                </AnimatePresence>
              </ul>
            </section>
          );
        })}
      </div>
    </LayoutGroup>
  );
}
