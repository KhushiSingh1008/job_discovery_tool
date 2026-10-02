import { AnimatePresence, motion } from "motion/react";
import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import { useFacets, useListings } from "../api/queries";
import type { ListingQuery, SortOrder } from "../api/types";
import { Page } from "../components/layout/Page";
import { SkylineHero } from "../components/three/Scenes";
import { Button } from "../components/ui/Button";
import { Skeleton, StateMessage } from "../components/ui/States";
import { FilterPanel } from "../features/listings/FilterPanel";
import { ListingCard } from "../features/listings/ListingCard";
import { SearchBar } from "../features/listings/SearchBar";
import { countActiveFilters, parseFilters, serializeFilters } from "../lib/filters";
import styles from "./JobsPage.module.css";

const SORT_LABELS: Record<SortOrder, string> = {
  newest: "Newest first",
  pay: "Highest pay",
  trust: "Most trusted",
};

const listVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.045 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const } },
};

function Hero() {
  const { data: facets } = useFacets();
  const count = (type: string) => facets?.job_types.find((f) => f.value === type)?.count ?? 0;
  const total = facets?.job_types.reduce((sum, f) => sum + f.count, 0);

  return (
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.heroText}>
        <p className={styles.eyebrow}>For international students in the UK</p>
        <h1 id="hero-title" className={styles.heroTitle}>
          Work that fits your <em>visa</em>, your timetable and your rent.
        </h1>
        <p className={styles.heroLead}>
          Part-time shifts, graduate roles and internships from university and employer job boards,
          each checked for fair pay, scam signals and sponsorship.
        </p>
        {total !== undefined && (
          <dl className={styles.stats}>
            <div>
              <dt>Live jobs</dt>
              <dd>{total}</dd>
            </div>
            <div>
              <dt>Part-time</dt>
              <dd>{count("part-time")}</dd>
            </div>
            <div>
              <dt>Full-time</dt>
              <dd>{count("full-time")}</dd>
            </div>
            <div>
              <dt>Internships</dt>
              <dd>{count("internship")}</dd>
            </div>
          </dl>
        )}
      </div>
      <SkylineHero className={styles.heroScene} />
    </section>
  );
}

function ResultsSkeleton() {
  return (
    <div className={styles.grid} aria-busy="true" aria-label="Loading jobs">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className={styles.skeletonCard}>
          <Skeleton width="35%" />
          <Skeleton height="1.4rem" width="80%" />
          <Skeleton width="55%" />
          <Skeleton height="2rem" />
        </div>
      ))}
    </div>
  );
}

export function JobsPage() {
  const [params, setParams] = useSearchParams();
  const query = useMemo(() => parseFilters(params), [params]);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const { data, isPending, isError, refetch, isPlaceholderData } = useListings(query);
  const { data: facets } = useFacets();

  /** Apply a change; any filter change goes back to page 1. */
  const update = useCallback(
    (patch: Partial<ListingQuery>) =>
      setParams(serializeFilters({ ...query, page: 1, ...patch }), { preventScrollReset: true }),
    [query, setParams],
  );
  const onSearch = useCallback((q: string) => update({ q: q || undefined }), [update]);
  const reset = () => setParams(new URLSearchParams(), { preventScrollReset: true });

  const goToPage = (page: number) => {
    setParams(serializeFilters({ ...query, page }));
    document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / (query.page_size ?? 12))) : 1;
  const activeFilters = countActiveFilters(query);

  return (
    <Page title="Jobs">
      <Hero />

      <div className={styles.toolbar} id="results">
        <SearchBar value={query.q ?? ""} onSearch={onSearch} />
        <div className={styles.toolbarActions}>
          <Button
            className={styles.filterToggle}
            aria-expanded={filtersOpen}
            aria-controls="filters"
            onClick={() => setFiltersOpen((open) => !open)}
          >
            Filters{activeFilters > 0 ? ` (${activeFilters})` : ""}
          </Button>
          <label className="visually-hidden" htmlFor="sort">
            Sort by
          </label>
          <select
            id="sort"
            className={styles.sort}
            value={query.sort}
            onChange={(event) => update({ sort: event.target.value as SortOrder })}
          >
            {Object.entries(SORT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.layout}>
        <aside
          id="filters"
          className={`${styles.filters} ${filtersOpen ? styles.filtersOpen : ""}`}
          aria-label="Filters"
        >
          <FilterPanel query={query} facets={facets} onChange={update} onReset={reset} />
        </aside>

        <section className={styles.results} aria-live="polite" aria-busy={isPlaceholderData}>
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
            <>
              <p className={styles.count}>
                <strong>{data.total}</strong> {data.total === 1 ? "job" : "jobs"}
                {query.q ? ` for “${query.q}”` : ""}
              </p>
              <AnimatePresence mode="wait">
                <motion.ul
                  key={params.toString()}
                  className={`${styles.grid} ${isPlaceholderData ? styles.stale : ""}`}
                  variants={listVariants}
                  initial="hidden"
                  animate="show"
                  exit={{ opacity: 0, transition: { duration: 0.12 } }}
                >
                  {data.items.map((listing) => (
                    <motion.li key={listing.id} variants={itemVariants} className={styles.item}>
                      <ListingCard listing={listing} />
                    </motion.li>
                  ))}
                </motion.ul>
              </AnimatePresence>
              {totalPages > 1 && (
                <nav className={styles.pagination} aria-label="Pagination">
                  <Button
                    disabled={(query.page ?? 1) <= 1}
                    onClick={() => goToPage((query.page ?? 1) - 1)}
                  >
                    Previous
                  </Button>
                  <span className={styles.pageInfo}>
                    Page {query.page} of {totalPages}
                  </span>
                  <Button
                    disabled={(query.page ?? 1) >= totalPages}
                    onClick={() => goToPage((query.page ?? 1) + 1)}
                  >
                    Next
                  </Button>
                </nav>
              )}
            </>
          )}
        </section>
      </div>
    </Page>
  );
}
