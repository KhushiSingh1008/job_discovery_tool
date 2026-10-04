import { useState } from "react";

import { ApiError } from "../../api/client";
import { useListing } from "../../api/queries";
import type { Listing } from "../../api/types";
import { Avatar } from "../../components/ui/Avatar";
import { LinkButton } from "../../components/ui/Button";
import { Tag } from "../../components/ui/Chip";
import { Drawer } from "../../components/ui/Drawer";
import { Icon } from "../../components/ui/Icon";
import { Skeleton, StateMessage } from "../../components/ui/States";
import { TrustBadge } from "../../components/ui/TrustBadge";
import {
  ELIGIBILITY_HINTS,
  ELIGIBILITY_LABELS,
  JOB_TYPE_LABELS,
  formatPay,
  formatPostedDate,
} from "../../lib/format";
import { EnhancePanel } from "../resume/EnhancePanel";
import { JobActions } from "./JobActions";
import { ELIGIBILITY_TONES, SOURCE_LABELS } from "./labels";
import { TrustBreakdown } from "./TrustBreakdown";
import styles from "./JobDetail.module.css";

/** Descriptions longer than this start collapsed behind "Read more". */
const COLLAPSE_AT_CHARS = 700;

interface JobDetailProps {
  listingId: string;
  /** "page" is the whole screen (phones, shared links); "pane" sits beside the results. */
  variant: "page" | "pane";
}

function DetailSkeleton() {
  return (
    <div className={styles.skeleton} aria-busy="true" aria-label="Loading job">
      <Skeleton width="30%" />
      <Skeleton height="2.2rem" width="75%" />
      <Skeleton width="50%" />
      <Skeleton height="3rem" width="60%" />
      <Skeleton height="12rem" />
    </div>
  );
}

function Description({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const paragraphs = text.split(/\n{2,}/).filter(Boolean);
  if (paragraphs.length === 0) {
    return (
      <p className={styles.muted}>
        The listing has no description. Open the original posting for full details.
      </p>
    );
  }
  const collapsible = text.length > COLLAPSE_AT_CHARS;
  return (
    <>
      <div
        id="job-description"
        className={`${styles.description} ${collapsible && !expanded ? styles.collapsed : ""}`}
      >
        {paragraphs.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>
      {collapsible && (
        <button
          type="button"
          className={styles.readMore}
          aria-expanded={expanded}
          aria-controls="job-description"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Show less" : "Read more"}
        </button>
      )}
    </>
  );
}

function Detail({ listing, variant }: { listing: Listing; variant: JobDetailProps["variant"] }) {
  const [enhancing, setEnhancing] = useState(false);
  const Title = variant === "page" ? "h1" : "h2";
  const Heading = variant === "page" ? "h2" : "h3";

  return (
    <article className={`${styles.detail} ${styles[variant]}`}>
      <header className={styles.header}>
        <div className={styles.employerLine}>
          <Avatar name={listing.employer} size="lg" />
          <div>
            <p className={styles.employer}>{listing.employer}</p>
            <p className={styles.source}>via {SOURCE_LABELS[listing.source] ?? listing.source}</p>
          </div>
        </div>

        <Title className={styles.title}>{listing.title}</Title>

        <p className={styles.meta}>
          {listing.location && (
            <span>
              <Icon name="pin" size={16} /> {listing.location}
            </span>
          )}
          <span>
            <Icon name="briefcase" size={16} /> {JOB_TYPE_LABELS[listing.job_type]}
          </span>
          <span>
            <Icon name="clock" size={16} /> Posted{" "}
            <time dateTime={listing.posted_date}>
              {formatPostedDate(listing.posted_date).toLowerCase()}
            </time>
          </span>
        </p>

        <div className={styles.highlights}>
          <span className={styles.pay}>
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

        <JobActions listing={listing} onEnhance={() => setEnhancing(true)} />
      </header>

      <section className={styles.section} aria-labelledby="about-role">
        <Heading id="about-role">About the role</Heading>
        {listing.pay_hourly !== null && listing.pay_raw && (
          <p className={styles.muted}>Pay advertised as “{listing.pay_raw}”.</p>
        )}
        <Description text={listing.description} />
      </section>

      <section className={`${styles.section} ${styles.panel}`} aria-labelledby="trust-heading">
        <div className={styles.panelHead}>
          <div>
            <Heading id="trust-heading">Trust check</Heading>
            <p className={styles.muted}>
              Scored from what the advert shows: who posted it, pay, scam phrases and age.
            </p>
          </div>
          <TrustBadge score={listing.trust_score} size="lg" />
        </div>
        <TrustBreakdown flags={listing.trust_flags} />
      </section>

      <section className={`${styles.section} ${styles.panel}`} aria-labelledby="visa-heading">
        <Heading id="visa-heading">Visa fit</Heading>
        <p>
          <Tag tone={ELIGIBILITY_TONES[listing.eligibility_tag]}>
            {ELIGIBILITY_LABELS[listing.eligibility_tag]}
          </Tag>
        </p>
        <p className={styles.muted}>{ELIGIBILITY_HINTS[listing.eligibility_tag]}</p>
      </section>

      <section className={`${styles.section} ${styles.fit}`} aria-labelledby="fit-heading">
        <div>
          <Heading id="fit-heading">How well do you fit?</Heading>
          <p className={styles.muted}>
            See which requirements your resume already covers, then tailor it line by line.
          </p>
        </div>
        <LinkButton to={`/match?listing=${listing.id}`} variant="secondary">
          Check my fit
        </LinkButton>
      </section>

      <Drawer
        open={enhancing}
        onClose={() => setEnhancing(false)}
        title="Enhance your resume"
        subtitle={`For ${listing.title} at ${listing.employer}`}
      >
        <EnhancePanel listingId={listing.id} />
      </Drawer>
    </article>
  );
}

/** Everything about one job: facts, actions, description, trust and visa fit. */
export function JobDetail({ listingId, variant }: JobDetailProps) {
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
  return <Detail listing={listing} variant={variant} />;
}
