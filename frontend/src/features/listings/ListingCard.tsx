import { Link } from "react-router";

import type { ListingSummary } from "../../api/types";
import { Tag } from "../../components/ui/Chip";
import { TrustBadge } from "../../components/ui/TrustBadge";
import {
  ELIGIBILITY_HINTS,
  ELIGIBILITY_LABELS,
  JOB_TYPE_LABELS,
  formatPay,
  formatPostedDate,
} from "../../lib/format";
import { ELIGIBILITY_TONES, SOURCE_LABELS } from "./labels";
import styles from "./ListingCard.module.css";

/** One search result: the six required fields at a glance, plus trust and visa fit. */
export function ListingCard({ listing }: { listing: ListingSummary }) {
  const payKnown = listing.pay_hourly !== null;
  return (
    <article className={styles.card}>
      <div className={styles.top}>
        <Tag tone="neutral">{JOB_TYPE_LABELS[listing.job_type]}</Tag>
        <time className={styles.posted} dateTime={listing.posted_date}>
          {formatPostedDate(listing.posted_date)}
        </time>
      </div>

      <h3 className={styles.title}>
        {/* The stretched link makes the whole card clickable without nesting interactives. */}
        <Link to={`/jobs/${listing.id}`} className={styles.link}>
          {listing.title}
        </Link>
      </h3>
      <p className={styles.meta}>
        <span className={styles.employer}>{listing.employer}</span>
        {listing.location && <span aria-hidden="true"> · </span>}
        {listing.location && <span>{listing.location}</span>}
      </p>

      <div className={styles.bottom}>
        <p className={`${styles.pay} ${payKnown ? "" : styles.payUnknown}`}>
          <span className="visually-hidden">Pay: </span>
          {formatPay(listing.pay_hourly, listing.pay_raw)}
        </p>
        <TrustBadge score={listing.trust_score} />
      </div>

      <div className={styles.footer}>
        <Tag
          tone={ELIGIBILITY_TONES[listing.eligibility_tag]}
          title={ELIGIBILITY_HINTS[listing.eligibility_tag]}
        >
          {ELIGIBILITY_LABELS[listing.eligibility_tag]}
        </Tag>
        <span className={styles.source}>via {SOURCE_LABELS[listing.source] ?? listing.source}</span>
      </div>
    </article>
  );
}
