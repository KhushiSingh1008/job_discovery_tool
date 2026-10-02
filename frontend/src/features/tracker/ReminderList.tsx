import { useUpdateApplication } from "../../api/queries";
import type { Reminder } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";
import styles from "./Tracker.module.css";

function ReminderCard({ reminder }: { reminder: Reminder }) {
  const { copied, copy } = useCopyToClipboard();
  const update = useUpdateApplication();

  return (
    <li className={styles.reminder}>
      <div className={styles.reminderHead}>
        <p>
          <strong>{reminder.title}</strong> at {reminder.employer}
        </p>
        <span className={styles.silent}>{reminder.days_silent} days quiet</span>
      </div>
      <details className={styles.draft}>
        <summary>Draft follow-up message</summary>
        <pre>{reminder.draft_message}</pre>
      </details>
      <div className={styles.reminderActions}>
        <Button size="sm" onClick={() => void copy(reminder.draft_message)}>
          {copied ? "Copied" : "Copy draft"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={update.isPending}
          onClick={() =>
            update.mutate({
              id: reminder.application_id,
              data: { last_contact_at: new Date().toISOString() },
            })
          }
        >
          I've followed up
        </Button>
      </div>
    </li>
  );
}

/** Applications with no reply for a week, each with a ready-to-send message. */
export function ReminderList({ reminders }: { reminders: Reminder[] }) {
  if (reminders.length === 0) return null;
  return (
    <section className={styles.reminders} aria-labelledby="reminders-heading">
      <h2 id="reminders-heading" className={styles.sectionTitle}>
        Time to follow up <span className={styles.badgeCount}>{reminders.length}</span>
      </h2>
      <ul>
        {reminders.map((reminder) => (
          <ReminderCard key={reminder.application_id} reminder={reminder} />
        ))}
      </ul>
    </section>
  );
}
