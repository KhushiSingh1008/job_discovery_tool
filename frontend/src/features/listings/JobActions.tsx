import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Link } from "react-router";

import { useApplications, useTrackJob, useUpdateApplication } from "../../api/queries";
import type { Listing } from "../../api/types";
import { Button, ExternalLinkButton } from "../../components/ui/Button";
import { Icon } from "../../components/ui/Icon";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";
import { SaveJobButton } from "../tracker/SaveJobButton";
import styles from "./JobDetail.module.css";

interface JobActionsProps {
  listing: Listing;
  onEnhance: () => void;
}

function ShareButton({ listing }: { listing: Listing }) {
  const { copied, copy } = useCopyToClipboard();

  const share = async () => {
    const url = `${window.location.origin}/jobs/${listing.id}`;
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({
          title: listing.title,
          text: `${listing.title} at ${listing.employer}`,
          url,
        });
        return;
      } catch {
        return; // the user closed the share sheet
      }
    }
    await copy(url);
  };

  const label = copied ? "Link copied" : "Share job";
  return (
    <Button variant="icon" aria-label={label} title={label} onClick={() => void share()}>
      <Icon name={copied ? "check" : "share"} />
    </Button>
  );
}

/**
 * After "Apply now" opens the employer's site, offer to record the application so the
 * tracker and the work-hour guard stay accurate without any extra steps.
 */
function ApplyFollowUp({ listing, onDismiss }: { listing: Listing; onDismiss: () => void }) {
  const { data: applications } = useApplications();
  const track = useTrackJob();
  const update = useUpdateApplication();
  const application = applications?.find((a) => a.listing_id === listing.id);
  const busy = track.isPending || update.isPending;
  const error = track.error ?? update.error;

  if (application && application.status !== "saved") {
    return (
      <p className={styles.followUp} role="status">
        <Icon name="check" size={16} /> Tracked as applied.{" "}
        <Link to="/tracker">Open your applications</Link>
      </p>
    );
  }

  const markApplied = () =>
    application
      ? update.mutate({ id: application.id, data: { status: "applied" } })
      : track.mutate({ listing_id: listing.id, status: "applied" });

  return (
    <div className={styles.followUp} role="status">
      <p>Did you apply on {listing.employer}'s site?</p>
      <div className={styles.followUpActions}>
        <Button size="sm" variant="primary" disabled={busy} onClick={markApplied}>
          Yes, mark as applied
        </Button>
        <Button size="sm" variant="ghost" onClick={onDismiss}>
          Not yet
        </Button>
      </div>
      {error && <p className={styles.error}>{error.message}</p>}
    </div>
  );
}

export function JobActions({ listing, onEnhance }: JobActionsProps) {
  const [askedAboutApplying, setAskedAboutApplying] = useState(false);

  return (
    <div className={styles.actionsBlock}>
      <div className={styles.actions}>
        <ExternalLinkButton
          variant="primary"
          size="lg"
          href={listing.url}
          className={styles.apply}
          onClick={() => setAskedAboutApplying(true)}
        >
          Apply now
          <span className={styles.applyArrow} aria-hidden="true">
            <Icon name="arrowRight" size={16} />
          </span>
          <span className="visually-hidden"> (opens the employer's site)</span>
        </ExternalLinkButton>
        <Button variant="secondary" size="lg" onClick={onEnhance}>
          <Icon name="sparkle" /> Enhance my resume
        </Button>
        <SaveJobButton listingId={listing.id} />
        <ShareButton listing={listing} />
      </div>
      <AnimatePresence>
        {askedAboutApplying && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          >
            <ApplyFollowUp listing={listing} onDismiss={() => setAskedAboutApplying(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
