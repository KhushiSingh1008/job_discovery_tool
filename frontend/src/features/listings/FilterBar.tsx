import {
  ELIGIBILITY_TAGS,
  JOB_TYPES,
  type FilterFacets,
  type ListingQuery,
  type SortOrder,
} from "../../api/types";
import { Button } from "../../components/ui/Button";
import { ToggleChip } from "../../components/ui/Chip";
import { ELIGIBILITY_LABELS, JOB_TYPE_LABELS } from "../../lib/format";
import { countActiveFilters, toggleValue } from "../../lib/filters";
import { FilterMenu } from "./FilterMenu";
import { LIVING_WAGE, SORT_LABELS } from "./labels";
import styles from "./FilterBar.module.css";

interface FilterBarProps {
  query: ListingQuery;
  facets: FilterFacets | undefined;
  onChange: (patch: Partial<ListingQuery>) => void;
  onReset: () => void;
}

interface Option {
  value: number;
  label: string;
}

const PAY_OPTIONS: Option[] = [
  { value: 0, label: "Any pay" },
  { value: 10, label: "£10/h or more" },
  { value: LIVING_WAGE, label: `£${LIVING_WAGE}/h+ (Living Wage)` },
  { value: 15, label: "£15/h or more" },
  { value: 20, label: "£20/h or more" },
];

const TRUST_OPTIONS: Option[] = [
  { value: 0, label: "Any" },
  { value: 50, label: "50+" },
  { value: 75, label: "Trusted (75+)" },
];

const POSTED_OPTIONS: Option[] = [
  { value: 0, label: "Any time" },
  { value: 1, label: "Past 24 hours" },
  { value: 7, label: "Past week" },
  { value: 30, label: "Past month" },
];

function RadioList({
  label,
  options,
  value,
  onSelect,
}: {
  label: string;
  options: Option[];
  value: number;
  onSelect: (value: number) => void;
}) {
  return (
    <div className={styles.radioList} role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          onClick={() => onSelect(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function countFor(
  facets: FilterFacets | undefined,
  key: "job_types" | "eligibility",
  value: string,
) {
  return facets?.[key].find((facet) => facet.value === value)?.count ?? 0;
}

/** Label for a multi-select pill: "Job type", "Internship" or "Job type · 2". */
function multiSummary(label: string, values: readonly string[], names: Record<string, string>) {
  if (values.length === 0) return undefined;
  if (values.length === 1) return names[values[0]!];
  return `${label} · ${values.length}`;
}

function optionSummary(options: Option[], value: number | undefined) {
  return value ? options.find((option) => option.value === value)?.label : undefined;
}

export function FilterBar({ query, facets, onChange, onReset }: FilterBarProps) {
  const active = countActiveFilters(query);
  const optional = (value: number) => (value > 0 ? value : undefined);
  const jobTypes = query.job_type ?? [];
  const eligibility = query.eligibility ?? [];

  return (
    <div className={styles.bar} role="toolbar" aria-label="Filters">
      <FilterMenu
        label="Job type"
        summary={multiSummary("Job type", jobTypes, JOB_TYPE_LABELS)}
        active={jobTypes.length > 0}
      >
        <div className={styles.chips}>
          {JOB_TYPES.map((type) => (
            <ToggleChip
              key={type}
              pressed={jobTypes.includes(type)}
              onToggle={() => onChange({ job_type: toggleValue(jobTypes, type) })}
              count={countFor(facets, "job_types", type)}
            >
              {JOB_TYPE_LABELS[type]}
            </ToggleChip>
          ))}
        </div>
      </FilterMenu>

      <FilterMenu
        label="Pay"
        summary={optionSummary(PAY_OPTIONS, query.min_pay)}
        active={Boolean(query.min_pay)}
      >
        <RadioList
          label="Minimum hourly pay"
          options={PAY_OPTIONS}
          value={query.min_pay ?? 0}
          onSelect={(value) => onChange({ min_pay: optional(value) })}
        />
      </FilterMenu>

      <FilterMenu
        label="Visa fit"
        summary={multiSummary("Visa fit", eligibility, ELIGIBILITY_LABELS)}
        active={eligibility.length > 0}
      >
        <div className={styles.chips}>
          {ELIGIBILITY_TAGS.filter((tag) => tag !== "unknown").map((tag) => (
            <ToggleChip
              key={tag}
              pressed={eligibility.includes(tag)}
              onToggle={() => onChange({ eligibility: toggleValue(eligibility, tag) })}
              count={countFor(facets, "eligibility", tag)}
            >
              {ELIGIBILITY_LABELS[tag]}
            </ToggleChip>
          ))}
        </div>
      </FilterMenu>

      <FilterMenu
        label="Trust score"
        summary={optionSummary(TRUST_OPTIONS, query.min_trust)}
        active={Boolean(query.min_trust)}
      >
        <RadioList
          label="Minimum trust score"
          options={TRUST_OPTIONS}
          value={query.min_trust ?? 0}
          onSelect={(value) => onChange({ min_trust: optional(value) })}
        />
      </FilterMenu>

      <FilterMenu
        label="Date posted"
        summary={optionSummary(POSTED_OPTIONS, query.posted_within_days)}
        active={Boolean(query.posted_within_days)}
        align="end"
      >
        <RadioList
          label="Posted within"
          options={POSTED_OPTIONS}
          value={query.posted_within_days ?? 0}
          onSelect={(value) => onChange({ posted_within_days: optional(value) })}
        />
      </FilterMenu>

      {active > 0 && (
        <Button variant="ghost" size="sm" onClick={onReset}>
          Clear all ({active})
        </Button>
      )}

      <label className={styles.sort}>
        <span>Sort by</span>
        <select
          value={query.sort ?? "newest"}
          onChange={(event) => onChange({ sort: event.target.value as SortOrder })}
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
