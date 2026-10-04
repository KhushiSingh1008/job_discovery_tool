import { useSources } from "../../api/queries";
import { formatRelativeTime } from "../../lib/format";
import styles from "./DataFreshness.module.css";

/**
 * How many jobs are live and how fresh they are, from the scraper's run history. A source
 * whose last run found nothing is called out, so stale data is never presented as current.
 */
export function DataFreshness() {
  const { data } = useSources();
  if (!data) return null;

  const open = data.reduce((sum, source) => sum + source.open_listings, 0);
  const active = data.filter((source) => source.open_listings > 0).length;
  const finished = data.flatMap((source) => (source.last_run ? [source.last_run.finished_at] : []));
  const latest = finished.sort().at(-1);
  const failing = data.filter(
    (source) => source.last_run?.status === "empty" || source.last_run?.status === "failed",
  );

  return (
    <p className={styles.freshness}>
      <span className={styles.dot} aria-hidden="true" />
      <span>
        <strong>{open}</strong> open jobs from {active} {active === 1 ? "source" : "sources"}
        {latest && <> · updated {formatRelativeTime(latest)}</>}
      </span>
      {failing.length > 0 && (
        <span className={styles.warning}>
          {failing.map((source) => source.label).join(", ")} could not be refreshed
        </span>
      )}
    </p>
  );
}
