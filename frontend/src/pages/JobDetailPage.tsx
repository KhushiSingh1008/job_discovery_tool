import { Link, useParams } from "react-router";

import { useListing } from "../api/queries";
import { Page } from "../components/layout/Page";
import { Icon } from "../components/ui/Icon";
import { JobDetail } from "../features/listings/JobDetail";
import styles from "./JobsPage.module.css";

/** A job on its own page: used on phones and for shared links. */
export function JobDetailPage() {
  const { listingId = "" } = useParams();
  const { data } = useListing(listingId); // shares the cache with JobDetail

  return (
    <Page title={data?.title ?? "Job"}>
      <div className={styles.detailPage}>
        <Link to="/" className={styles.back}>
          <Icon name="arrowRight" size={16} className={styles.backIcon} /> Back to jobs
        </Link>
        <JobDetail listingId={listingId} variant="page" />
      </div>
    </Page>
  );
}
