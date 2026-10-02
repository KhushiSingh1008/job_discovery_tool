import { motion } from "motion/react";
import { Link } from "react-router";

import { useDeleteApplication, useUpdateApplication } from "../../api/queries";
import type { Application } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { useSyncedState } from "../../hooks/useSyncedState";
import { formatPay } from "../../lib/format";
import { ACTION_LABELS, NEXT_STATUSES } from "../../lib/transitions";
import styles from "./Tracker.module.css";

/** A tracked application: weekly hours, next steps and removal. */
export function ApplicationCard({ application }: { application: Application }) {
  const update = useUpdateApplication();
  const remove = useDeleteApplication();
  const [hours, setHours] = useSyncedState(String(application.weekly_hours));

  const commitHours = () => {
    const value = Number(hours);
    if (!Number.isFinite(value) || value < 0 || value > 168) {
      setHours(String(application.weekly_hours));
      return;
    }
    if (value !== application.weekly_hours) {
      update.mutate({ id: application.id, data: { weekly_hours: value } });
    }
  };

  const hoursId = `hours-${application.id}`;

  return (
    <motion.li
      layout
      layoutId={`application-${application.id}`}
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94 }}
      transition={{ type: "spring", stiffness: 420, damping: 34 }}
      className={styles.appCard}
    >
      <Link to={`/jobs/${application.listing_id}`} className={styles.appTitle}>
        {application.title}
      </Link>
      <p className={styles.appMeta}>
        {application.employer} · {formatPay(application.pay_hourly, null)}
      </p>

      <div className={styles.hoursField}>
        <label htmlFor={hoursId}>Hours/week</label>
        <input
          id={hoursId}
          type="number"
          inputMode="decimal"
          min={0}
          max={168}
          step={0.5}
          value={hours}
          onChange={(event) => setHours(event.target.value)}
          onBlur={commitHours}
          onKeyDown={(event) => event.key === "Enter" && event.currentTarget.blur()}
        />
      </div>

      {update.isError && (
        <p role="alert" className={styles.appError}>
          {update.error.message}
        </p>
      )}

      <div className={styles.appActions}>
        {NEXT_STATUSES[application.status].map((status) => (
          <Button
            key={status}
            size="sm"
            variant={status === "rejected" ? "ghost" : "secondary"}
            disabled={update.isPending}
            onClick={() => update.mutate({ id: application.id, data: { status } })}
          >
            {ACTION_LABELS[status]}
          </Button>
        ))}
        <Button
          size="sm"
          variant="danger"
          disabled={remove.isPending}
          onClick={() => remove.mutate(application.id)}
          aria-label={`Remove ${application.title} from tracker`}
        >
          Remove
        </Button>
      </div>
    </motion.li>
  );
}
