import type { ReactNode } from "react";

import { ELIGIBILITY_TAGS, JOB_TYPES, type FilterFacets, type ListingQuery } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { ToggleChip } from "../../components/ui/Chip";
import { ELIGIBILITY_LABELS, JOB_TYPE_LABELS } from "../../lib/format";
import { countActiveFilters, toggleValue } from "../../lib/filters";
import { LIVING_WAGE } from "./labels";
import styles from "./FilterPanel.module.css";

interface FilterPanelProps {
  query: ListingQuery;
  facets: FilterFacets | undefined;
  onChange: (patch: Partial<ListingQuery>) => void;
  onReset: () => void;
}

const PAY_OPTIONS = [
  { value: 0, label: "Any pay" },
  { value: 10, label: "£10/h or more" },
  { value: LIVING_WAGE, label: `£${LIVING_WAGE}/h+ (Living Wage)` },
  { value: 15, label: "£15/h or more" },
  { value: 20, label: "£20/h or more" },
];

const TRUST_OPTIONS = [
  { value: 0, label: "Any" },
  { value: 50, label: "50+" },
  { value: 75, label: "Trusted (75+)" },
];

const POSTED_OPTIONS = [
  { value: 0, label: "Any time" },
  { value: 7, label: "Past week" },
  { value: 30, label: "Past month" },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className={styles.section}>
      <legend className={styles.legend}>{title}</legend>
      {children}
    </fieldset>
  );
}

function countFor(
  facets: FilterFacets | undefined,
  key: "job_types" | "eligibility",
  value: string,
) {
  return facets?.[key].find((facet) => facet.value === value)?.count;
}

export function FilterPanel({ query, facets, onChange, onReset }: FilterPanelProps) {
  const active = countActiveFilters(query);
  const optionalValue = (value: number) => (value > 0 ? value : undefined);

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.heading}>Filters</h2>
        {active > 0 && (
          <Button variant="ghost" size="sm" onClick={onReset}>
            Clear {active}
          </Button>
        )}
      </div>

      <Section title="Job type">
        <div className={styles.chips}>
          {JOB_TYPES.map((type) => (
            <ToggleChip
              key={type}
              pressed={query.job_type?.includes(type) ?? false}
              onToggle={() => onChange({ job_type: toggleValue(query.job_type, type) })}
              count={countFor(facets, "job_types", type) ?? 0}
            >
              {JOB_TYPE_LABELS[type]}
            </ToggleChip>
          ))}
        </div>
      </Section>

      <Section title="Visa fit">
        <div className={styles.chips}>
          {ELIGIBILITY_TAGS.filter((tag) => tag !== "unknown").map((tag) => (
            <ToggleChip
              key={tag}
              pressed={query.eligibility?.includes(tag) ?? false}
              onToggle={() => onChange({ eligibility: toggleValue(query.eligibility, tag) })}
              count={countFor(facets, "eligibility", tag) ?? 0}
            >
              {ELIGIBILITY_LABELS[tag]}
            </ToggleChip>
          ))}
        </div>
      </Section>

      <Section title="Location">
        <label className="visually-hidden" htmlFor="filter-location">
          Location
        </label>
        <select
          id="filter-location"
          className={styles.select}
          value={query.location ?? ""}
          onChange={(event) => onChange({ location: event.target.value || undefined })}
        >
          <option value="">Anywhere</option>
          {facets?.locations.map((facet) => (
            <option key={facet.value} value={facet.value}>
              {facet.value} ({facet.count})
            </option>
          ))}
        </select>
      </Section>

      <Section title="Pay">
        <label className="visually-hidden" htmlFor="filter-pay">
          Minimum hourly pay
        </label>
        <select
          id="filter-pay"
          className={styles.select}
          value={query.min_pay ?? 0}
          onChange={(event) => onChange({ min_pay: optionalValue(Number(event.target.value)) })}
        >
          {PAY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </Section>

      <Section title="Trust score">
        <div className={styles.segmented} role="radiogroup" aria-label="Minimum trust score">
          {TRUST_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={(query.min_trust ?? 0) === option.value}
              onClick={() => onChange({ min_trust: optionalValue(option.value) })}
            >
              {option.label}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Posted">
        <div className={styles.segmented} role="radiogroup" aria-label="Posted within">
          {POSTED_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={(query.posted_within_days ?? 0) === option.value}
              onClick={() => onChange({ posted_within_days: optionalValue(option.value) })}
            >
              {option.label}
            </button>
          ))}
        </div>
      </Section>
    </div>
  );
}
