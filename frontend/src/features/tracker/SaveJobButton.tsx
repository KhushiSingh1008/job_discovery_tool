import { useApplications, useDeleteApplication, useTrackJob } from "../../api/queries";
import { Button } from "../../components/ui/Button";
import { Icon } from "../../components/ui/Icon";
import { STATUS_LABELS } from "../../lib/format";

interface SaveJobButtonProps {
  listingId: string;
  className?: string;
}

/**
 * Bookmark a job. Saving adds it to the tracker as "Saved"; un-saving removes it, but only
 * while it is still just saved, so an application in progress is never lost by a misclick.
 */
export function SaveJobButton({ listingId, className }: SaveJobButtonProps) {
  const { data: applications } = useApplications();
  const track = useTrackJob();
  const remove = useDeleteApplication();

  const application = applications?.find((a) => a.listing_id === listingId);
  const busy = track.isPending || remove.isPending;
  const inProgress = application !== undefined && application.status !== "saved";

  const label = inProgress
    ? `In your tracker: ${STATUS_LABELS[application.status]}`
    : application
      ? "Saved. Remove from saved jobs"
      : "Save job";

  const toggle = () => {
    if (!application) track.mutate({ listing_id: listingId });
    else if (!inProgress) remove.mutate(application.id);
  };

  return (
    <Button
      variant="icon"
      className={className}
      aria-label={label}
      title={label}
      aria-pressed={application !== undefined}
      disabled={busy || inProgress || applications === undefined}
      onClick={toggle}
    >
      <Icon name="bookmark" filled={application !== undefined} />
    </Button>
  );
}
