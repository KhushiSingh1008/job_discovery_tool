import { useApplications, useHoursSummary, useReminders } from "../api/queries";
import { Page } from "../components/layout/Page";
import { Button, LinkButton } from "../components/ui/Button";
import { Skeleton, StateMessage } from "../components/ui/States";
import { HoursPanel } from "../features/tracker/HoursPanel";
import { ReminderList } from "../features/tracker/ReminderList";
import { TrackerBoard } from "../features/tracker/TrackerBoard";
import { VisaSettingsBar } from "../features/tracker/VisaSettingsBar";
import { useVisaSettings } from "../hooks/useVisaSettings";
import styles from "./TrackerPage.module.css";

export function TrackerPage() {
  const [settings, setSettings] = useVisaSettings();
  const applications = useApplications();
  const hours = useHoursSummary(settings);
  const reminders = useReminders();

  return (
    <Page title="Tracker">
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Your applications</h1>
          <p className={styles.lead}>
            Track every application and keep your weekly hours inside your visa limit.
          </p>
        </div>
        <VisaSettingsBar settings={settings} onChange={setSettings} />
      </header>

      <div className={styles.stack}>
        {hours.data ? <HoursPanel summary={hours.data} /> : <Skeleton height="16rem" />}

        <ReminderList reminders={reminders.data ?? []} />

        <section aria-labelledby="board-heading">
          <h2 id="board-heading" className={styles.sectionTitle}>
            Pipeline
          </h2>
          {applications.isPending ? (
            <Skeleton height="14rem" />
          ) : applications.isError ? (
            <StateMessage
              tone="error"
              title="We couldn't load your tracker"
              action={<Button onClick={() => void applications.refetch()}>Try again</Button>}
            >
              {applications.error.message}
            </StateMessage>
          ) : applications.data.length === 0 ? (
            <StateMessage
              title="Nothing tracked yet"
              action={
                <LinkButton to="/" variant="primary">
                  Browse jobs
                </LinkButton>
              }
            >
              Open a job and choose “Track this job”. Add the weekly hours of jobs you are offered
              and the tracker will warn you before you go over your visa limit.
            </StateMessage>
          ) : (
            <TrackerBoard applications={applications.data} />
          )}
        </section>
      </div>
    </Page>
  );
}
