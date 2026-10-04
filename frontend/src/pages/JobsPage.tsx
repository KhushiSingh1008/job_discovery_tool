import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { useSearchParams, type To } from "react-router";

import { useFacets, useListings } from "../api/queries";
import { JOB_TYPES, type ListingQuery } from "../api/types";
import { Page } from "../components/layout/Page";
import { SkylineHero } from "../components/three/Scenes";
import { Button } from "../components/ui/Button";
import { ToggleChip } from "../components/ui/Chip";
import { Skeleton, StateMessage } from "../components/ui/States";
import { FilterBar } from "../features/listings/FilterBar";
import { JobDetail } from "../features/listings/JobDetail";
import { JobRow } from "../features/listings/JobRow";
import { SearchBar, type SearchValues } from "../features/listings/SearchBar";
import { SPLIT_VIEW_QUERY, useMediaQuery } from "../hooks/useMediaQuery";
import { countActiveFilters, parseFilters, serializeFilters, toggleValue } from "../lib/filters";
import { JOB_TYPE_LABELS } from "../lib/format";
import styles from "./JobsPage.module.css";

/** Search param holding the job shown in the side pane (wide screens only). */
const SELECTED_PARAM = "job";

const listVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.035 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] as const } },
};

function ResultsSkeleton() {
  return (
    <div className={styles.list} aria-busy="true" aria-label="Loading jobs">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className={styles.skeletonRow}>
          <Skeleton height="2.75rem" width="2.75rem" />
          <div className={styles.skeletonText}>
            <Skeleton height="1.1rem" width="70%" />
            <Skeleton width="45%" />
            <Skeleton width="60%" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function JobsPage() {
  const [params, setParams] = useSearchParams();
  const query = useMemo(() => parseFilters(params), [params]);
  const splitView = useMediaQuery(SPLIT_VIEW_QUERY);
  const pane = useRef<HTMLElement>(null);

  const { data, isPending, isError, refetch, isPlaceholderData } = useListings(query);
  const { data: facets } = useFacets();

  /** Apply a change; any filter change goes back to page 1 and drops the selection. */
  const update = useCallback(
    (patch: Partial<ListingQuery>) =>
      setParams(serializeFilters({ ...query, page: 1, ...patch }), { preventScrollReset: true }),
    [query, setParams],
  );
  const onSearch = useCallback(
    (values: Partial<SearchValues>) => {
      const patch: Partial<ListingQuery> = {};
      if (values.q !== undefined) patch.q = values.q || undefined;
      if (values.location !== undefined) patch.location = values.location || undefined;
      update(patch);
    },
    [update],
  );
  const reset = () => setParams(new URLSearchParams(), { preventScrollReset: true });

  const goToPage = (page: number) => {
    setParams(serializeFilters({ ...query, page }));
    document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Wide screens show a job beside the list: the chosen one, or the first result.
  const selectedId = splitView ? (params.get(SELECTED_PARAM) ?? data?.items[0]?.id) : undefined;
  const rowTarget = (id: string): To => {
    if (!splitView) return `/jobs/${id}`;
    const next = new URLSearchParams(params);
    next.set(SELECTED_PARAM, id);
    return { search: `?${next.toString()}` };
  };

  useEffect(() => {
    if (pane.current) pane.current.scrollTop = 0;
  }, [selectedId]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / (query.page_size ?? 12))) : 1;
  const activeFilters = countActiveFilters(query);
  const jobTypeCount = (type: string) =>
    facets?.job_types.find((facet) => facet.value === type)?.count ?? 0;

  return (
    <Page title="Find jobs">
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroText}>
          <p className={styles.eyebrow}>For international students in the UK</p>
          <h1 id="hero-title" className={styles.heroTitle}>
            Find work that fits your <span>visa</span> and your timetable
          </h1>
          <p className={styles.heroLead}>
            Part-time shifts, graduate roles and internships, each checked for fair pay, scam
            signals and visa sponsorship.
          </p>
        </div>
        {splitView && <SkylineHero className={styles.heroScene} />}
        <div className={styles.heroSearch}>
          <SearchBar
            q={query.q ?? ""}
            location={query.location ?? ""}
            locations={facets?.locations.map((facet) => facet.value) ?? []}
            onSearch={onSearch}
          />
          <div className={styles.quick} role="group" aria-label="Quick filters">
            {JOB_TYPES.map((type) => (
              <ToggleChip
                key={type}
                pressed={query.job_type?.includes(type) ?? false}
                onToggle={() => update({ job_type: toggleValue(query.job_type, type) })}
                count={jobTypeCount(type)}
              >
                {JOB_TYPE_LABELS[type]}
              </ToggleChip>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.toolbar} id="results">
        <FilterBar query={query} facets={facets} onChange={update} onReset={reset} />
      </div>

      {isPending ? (
        <ResultsSkeleton />
      ) : isError ? (
        <StateMessage
          tone="error"
          title="We couldn't load jobs"
          action={<Button onClick={() => void refetch()}>Try again</Button>}
        >
          The job service may be starting up. Check that the backend is running, then retry.
        </StateMessage>
      ) : data.items.length === 0 ? (
        <StateMessage
          title="No jobs match these filters"
          action={
            activeFilters > 0 || query.q ? <Button onClick={reset}>Clear search</Button> : null
          }
        >
          Try fewer filters or a broader search term, such as a city or a job family.
        </StateMessage>
      ) : (
        <div className={styles.split}>
          <section
            className={styles.resultsColumn}
            aria-label="Job results"
            aria-live="polite"
            aria-busy={isPlaceholderData}
          >
            <p className={styles.count}>
              <strong>{data.total}</strong> matching {data.total === 1 ? "job" : "jobs"}
              {query.q ? ` for “${query.q}”` : ""}
            </p>
            <AnimatePresence mode="wait">
              <motion.ul
                key={serializeFilters(query).toString()}
                className={`${styles.list} ${isPlaceholderData ? styles.stale : ""}`}
                variants={listVariants}
                initial="hidden"
                animate="show"
                exit={{ opacity: 0, transition: { duration: 0.12 } }}
              >
                {data.items.map((listing) => (
                  <motion.li key={listing.id} variants={itemVariants}>
                    <JobRow
                      listing={listing}
                      to={rowTarget(listing.id)}
                      selected={listing.id === selectedId}
                    />
                  </motion.li>
                ))}
              </motion.ul>
            </AnimatePresence>
            {totalPages > 1 && (
              <nav className={styles.pagination} aria-label="Pagination">
                <Button
                  size="sm"
                  disabled={(query.page ?? 1) <= 1}
                  onClick={() => goToPage((query.page ?? 1) - 1)}
                >
                  Previous
                </Button>
                <span className={styles.pageInfo}>
                  Page {query.page} of {totalPages}
                </span>
                <Button
                  size="sm"
                  disabled={(query.page ?? 1) >= totalPages}
                  onClick={() => goToPage((query.page ?? 1) + 1)}
                >
                  Next
                </Button>
              </nav>
            )}
          </section>

          {selectedId && (
            <aside ref={pane} className={styles.pane} aria-label="Job details">
              <AnimatePresence mode="wait">
                <motion.div
                  key={selectedId}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, transition: { duration: 0.1 } }}
                  transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                >
                  <JobDetail listingId={selectedId} variant="pane" />
                </motion.div>
              </AnimatePresence>
            </aside>
          )}
        </div>
      )}
    </Page>
  );
}
