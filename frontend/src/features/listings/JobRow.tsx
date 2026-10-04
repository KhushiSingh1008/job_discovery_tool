import { Link, type To } from "react-router";

import type { ListingSummary } from "../../api/types";
import { Avatar } from "../../components/ui/Avatar";
import { Tag } from "../../components/ui/Chip";
import { TrustBadge } from "../../components/ui/TrustBadge";
import {
  ELIGIBILITY_HINTS,
  ELIGIBILITY_LABELS,
  JOB_TYPE_LABELS,
  formatPay,
  formatPostedDate,
} from "../../lib/format";
import { SaveJobButton } from "../tracker/SaveJobButton";
import { ELIGIBILITY_TONES } from "./labels";
import styles from "./JobRow.module.css";

interface JobRowProps {
  listing: ListingSummary;
  /** Where the row leads: the side pane on wide screens, the job page on phones. */
  to?: To;
  selected?: boolean;
}

/** One search result: the six required fields at a glance, plus trust and visa fit. */
export function JobRow({ listing, to = `/jobs/${listing.id}`, selected = false }: JobRowProps) {
  const payKnown = listing.pay_hourly !== null;
  return (
    <article className={`${styles.row} ${selected ? styles.selected : ""}`}>
      <Avatar name={listing.employer} />

      <div className={styles.main}>
        <h3 className={styles.title}>
          {/* The stretched link makes the whole row clickable without nesting interactives. */}
          <Link
            to={to}
            className={styles.link}
            aria-current={selected ? "true" : undefined}
            preventScrollReset
          >
            {listing.title}
          </Link>
        </h3>
        <p className={styles.employer}>{listing.employer}</p>
        <p className={styles.meta}>
          {listing.location && <span>{listing.location}</span>}
          <span>{JOB_TYPE_LABELS[listing.job_type]}</span>
        </p>
        <div className={styles.footer}>
          <span className={`${styles.pay} ${payKnown ? "" : styles.payUnknown}`}>
            <span className="visually-hidden">Pay: </span>
            {formatPay(listing.pay_hourly, listing.pay_raw)}
          </span>
          <Tag
            tone={ELIGIBILITY_TONES[listing.eligibility_tag]}
            title={ELIGIBILITY_HINTS[listing.eligibility_tag]}
          >
            {ELIGIBILITY_LABELS[listing.eligibility_tag]}
          </Tag>
          <TrustBadge score={listing.trust_score} />
        </div>
      </div>

      <div className={styles.side}>
        <SaveJobButton listingId={listing.id} className={styles.save} />
        <time className={styles.posted} dateTime={listing.posted_date}>
          {formatPostedDate(listing.posted_date)}
        </time>
      </div>
    </article>
  );
}
