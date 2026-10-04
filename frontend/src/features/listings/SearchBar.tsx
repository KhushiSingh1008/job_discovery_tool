import { useEffect, useId, useRef, type FormEvent } from "react";

import { Icon } from "../../components/ui/Icon";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useSyncedState } from "../../hooks/useSyncedState";
import styles from "./SearchBar.module.css";

export interface SearchValues {
  q: string;
  location: string;
}

interface SearchBarProps extends SearchValues {
  locations: string[];
  onSearch: (values: Partial<SearchValues>) => void;
}

/**
 * Text that follows its URL value (back button, "clear all") and commits to the URL once
 * typing settles.
 */
function useDebouncedField(external: string, commit: (value: string) => void, delayMs: number) {
  const [text, setText] = useSyncedState(external);
  const debounced = useDebouncedValue(text, delayMs);
  const lastDebounced = useRef(debounced);

  // Commit only when the *typed* text settles, never because the URL changed; otherwise
  // clearing filters would race with the stale debounced text and restore the old query.
  useEffect(() => {
    if (debounced === lastDebounced.current) return;
    lastDebounced.current = debounced;
    if (debounced.trim() !== external) commit(debounced.trim());
  }, [debounced, external, commit]);

  return [text, setText] as const;
}

/** Keyword + location search: live as you type, or immediately on Search. */
export function SearchBar({ q, location, locations, onSearch }: SearchBarProps) {
  const listId = useId();
  const [keyword, setKeyword] = useDebouncedField(q, (value) => onSearch({ q: value }), 300);
  const [place, setPlace] = useDebouncedField(
    location,
    (value) => onSearch({ location: value }),
    500,
  );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch({ q: keyword.trim(), location: place.trim() });
  };

  return (
    <form className={styles.search} role="search" onSubmit={submit}>
      <div className={styles.field}>
        <Icon name="search" className={styles.icon} />
        <label htmlFor="job-search" className="visually-hidden">
          Search jobs
        </label>
        <input
          id="job-search"
          type="search"
          className={styles.input}
          placeholder="Job title, employer or keyword"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          autoComplete="off"
        />
      </div>
      <span className={styles.divider} aria-hidden="true" />
      <div className={styles.field}>
        <Icon name="pin" className={styles.icon} />
        <label htmlFor="job-location" className="visually-hidden">
          Location
        </label>
        <input
          id="job-location"
          type="search"
          className={styles.input}
          placeholder="City, or “remote”"
          list={listId}
          value={place}
          onChange={(event) => setPlace(event.target.value)}
          autoComplete="off"
        />
        <datalist id={listId}>
          {locations.map((name) => (
            <option key={name} value={name} />
          ))}
        </datalist>
      </div>
      <button type="submit" className={styles.submit}>
        Search
      </button>
    </form>
  );
}
