import type { HoursStatus, HoursSummary } from "../../api/types";
import { HoursRing } from "../../components/three/Scenes";
import { formatHours } from "../../lib/format";
import styles from "./Tracker.module.css";

const TONES: Record<HoursStatus, "good" | "warn" | "bad" | "teal"> = {
  ok: "good",
  near_limit: "warn",
  over_limit: "bad",
  no_limit: "teal",
};

const HEADLINES: Record<HoursStatus, string> = {
  ok: "Within your limit",
  near_limit: "Close to your limit",
  over_limit: "Over your limit",
  no_limit: "No weekly limit",
};

/** The work-hour guard: a 3D gauge plus a plain-language verdict. */
export function HoursPanel({ summary }: { summary: HoursSummary }) {
  const cap = summary.cap_hours;
  const committedFraction = cap ? summary.committed_hours / cap : 0;
  const potentialFraction = cap ? summary.potential_hours / cap : 0;

  return (
    <section
      className={`${styles.hoursPanel} ${styles[summary.status]}`}
      aria-labelledby="hours-heading"
    >
      <div className={styles.gauge}>
        <HoursRing
          className={styles.ring}
          committedFraction={committedFraction}
          potentialFraction={potentialFraction}
          tone={TONES[summary.status]}
        />
        <div className={styles.gaugeLabel}>
          <span className={styles.gaugeValue}>{formatHours(summary.committed_hours)}</span>
          <span className={styles.gaugeCap}>
            {cap === null ? "no limit" : `of ${formatHours(cap)} / week`}
          </span>
        </div>
      </div>

      <div className={styles.verdict}>
        <p className={styles.eyebrow}>{summary.rule_label}</p>
        <h2 id="hours-heading" className={styles.verdictTitle}>
          {HEADLINES[summary.status]}
        </h2>
        <p role="status">{summary.message}</p>
        <dl className={styles.hoursFacts}>
          <div>
            <dt>Committed (offers)</dt>
            <dd>{formatHours(summary.committed_hours)}</dd>
          </div>
          <div>
            <dt>If interviews succeed</dt>
            <dd>{formatHours(summary.potential_hours)}</dd>
          </div>
          {summary.remaining_hours !== null && (
            <div>
              <dt>Left this week</dt>
              <dd>{formatHours(Math.max(0, summary.remaining_hours))}</dd>
            </div>
          )}
        </dl>
        {summary.vacation_note && <p className={styles.note}>{summary.vacation_note}</p>}
        {summary.source_url && (
          <a className={styles.note} href={summary.source_url} target="_blank" rel="noreferrer">
            Check the official rules ↗
          </a>
        )}
      </div>
    </section>
  );
}
