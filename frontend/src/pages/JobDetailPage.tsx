import { motion } from "motion/react";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/client";
import { useListing, useTrackJob } from "../api/queries";
import type { Listing, TrustFlag } from "../api/types";
import { Page } from "../components/layout/Page";
import { Button, LinkButton } from "../components/ui/Button";
import { Tag } from "../components/ui/Chip";
import { Skeleton, StateMessage } from "../components/ui/States";
import { TrustBadge } from "../components/ui/TrustBadge";
import { ELIGIBILITY_TONES, SOURCE_LABELS } from "../features/listings/labels";
import {
  ELIGIBILITY_HINTS,
  ELIGIBILITY_LABELS,
  JOB_TYPE_LABELS,
  formatPay,
  formatPostedDate,
} from "../lib/format";
import styles from "./JobDetailPage.module.css";

const MAX_IMPACT = 35;

function TrustBreakdown({ flags }: { flags: TrustFlag[] }) {
  const sorted = [...flags].sort((a, b) => a.impact - b.impact); // concerns first
  return (
    <ul className={styles.flags}>
      {sorted.map((flag, index) => {
        const tone = flag.impact > 0 ? "good" : flag.impact < 0 ? "bad" : "neutral";
        const width = `${(Math.min(Math.abs(flag.impact), MAX_IMPACT) / MAX_IMPACT) * 100}%`;
        return (
          <motion.li
            key={flag.code}
            className={`${styles.flag} ${styles[tone]}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 + index * 0.06 }}
          >
            <span className={styles.impact}>
              {flag.impact > 0 ? `+${flag.impact}` : flag.impact === 0 ? "±0" : flag.impact}
            </span>
            <span className={styles.flagText}>{flag.message}</span>
            <span className={styles.bar} aria-hidden="true">
              <motion.span
                initial={{ width: 0 }}
                animate={{ width }}
                transition={{ delay: 0.25 + index * 0.06, duration: 0.5 }}
              />
            </span>
          </motion.li>
        );
      })}
    </ul>
  );
}

function TrackButton({ listing }: { listing: Listing }) {
  const track = useTrackJob();
  const alreadyTracked = track.error instanceof ApiError && track.error.status === 409;

  if (track.isSuccess || alreadyTracked) {
    return (
      <LinkButton to="/tracker" variant="secondary">
        {alreadyTracked ? "Already in your tracker" : "Added. Open tracker"} →
      </LinkButton>
    );
  }
  return (
    <>
      <Button
        variant="primary"
        disabled={track.isPending}
        onClick={() => track.mutate({ listing_id: listing.id })}
      >
        {track.isPending ? "Adding…" : "Track this job"}
      </Button>
      {track.isError && (
        <p role="alert" className={styles.error}>
          {track.error.message}
        </p>
      )}
    </>
  );
}

function DetailSkeleton() {
  return (
    <div className={styles.skeleton} aria-busy="true" aria-label="Loading job">
      <Skeleton width="30%" />
      <Skeleton height="2.4rem" width="70%" />
      <Skeleton width="45%" />
      <Skeleton height="10rem" />
    </div>
  );
}

export function JobDetailPage() {
  const { listingId = "" } = useParams();
  const { data: listing, isPending, isError, error } = useListing(listingId);

  if (isPending) return <DetailSkeleton />;
  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <StateMessage
        tone={notFound ? "neutral" : "error"}
        title={notFound ? "This job is no longer listed" : "We couldn't load this job"}
        action={<LinkButton to="/">Back to jobs</LinkButton>}
      >
        {notFound ? "It may have been filled or removed by the employer." : error.message}
      </StateMessage>
    );
  }

  const paragraphs = listing.description.split(/\n{2,}/).filter(Boolean);

  return (
    <Page title={listing.title}>
      <nav className={styles.breadcrumb} aria-label="Breadcrumb">
        <Link to="/">Jobs</Link> <span aria-hidden="true">/</span> {listing.employer}
      </nav>

      <header className={styles.header}>
        <div className={styles.headline}>
          <div className={styles.tags}>
            <Tag>{JOB_TYPE_LABELS[listing.job_type]}</Tag>
            <Tag tone={ELIGIBILITY_TONES[listing.eligibility_tag]}>
              {ELIGIBILITY_LABELS[listing.eligibility_tag]}
            </Tag>
          </div>
          <h1 className={styles.title}>{listing.title}</h1>
          <p className={styles.employer}>
            {listing.employer}
            {listing.location && <span> · {listing.location}</span>}
          </p>
        </div>
        <div className={styles.actions}>
          <TrackButton listing={listing} />
          <LinkButton to={`/match?listing=${listing.id}`}>Check my fit</LinkButton>
          <a className={styles.external} href={listing.url} target="_blank" rel="noreferrer">
            View original posting ↗
          </a>
        </div>
      </header>

      <dl className={styles.facts}>
        <div>
          <dt>Pay</dt>
          <dd className={styles.mono}>{formatPay(listing.pay_hourly, listing.pay_raw)}</dd>
          {listing.pay_hourly !== null && listing.pay_raw && (
            <dd className={styles.factNote}>Advertised as “{listing.pay_raw}”</dd>
          )}
        </div>
        <div>
          <dt>Posted</dt>
          <dd>
            <time dateTime={listing.posted_date}>{formatPostedDate(listing.posted_date)}</time>
          </dd>
        </div>
        <div>
          <dt>Location</dt>
          <dd>{listing.location || "Not stated"}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{SOURCE_LABELS[listing.source] ?? listing.source}</dd>
        </div>
      </dl>

      <div className={styles.body}>
        <section className={styles.description} aria-labelledby="about-role">
          <h2 id="about-role">About the role</h2>
          {paragraphs.length > 0 ? (
            paragraphs.map((text, i) => <p key={i}>{text}</p>)
          ) : (
            <p className={styles.muted}>
              The listing has no description. Open the original posting for full details.
            </p>
          )}
        </section>

        <aside className={styles.side}>
          <section className={styles.panel} aria-labelledby="trust-heading">
            <div className={styles.panelHead}>
              <h2 id="trust-heading">Trust check</h2>
              <TrustBadge score={listing.trust_score} size="lg" />
            </div>
            <p className={styles.muted}>
              Scored from what the advert shows: who posted it, pay, scam phrases and age.
            </p>
            <TrustBreakdown flags={listing.trust_flags} />
          </section>

          <section className={styles.panel} aria-labelledby="visa-heading">
            <h2 id="visa-heading">Visa fit</h2>
            <p>
              <Tag tone={ELIGIBILITY_TONES[listing.eligibility_tag]}>
                {ELIGIBILITY_LABELS[listing.eligibility_tag]}
              </Tag>
            </p>
            <p className={styles.muted}>{ELIGIBILITY_HINTS[listing.eligibility_tag]}</p>
          </section>
        </aside>
      </div>
    </Page>
  );
}
