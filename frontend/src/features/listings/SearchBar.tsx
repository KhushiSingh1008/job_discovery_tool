import { useEffect, useRef, type FormEvent } from "react";

import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useSyncedState } from "../../hooks/useSyncedState";
import styles from "./SearchBar.module.css";

interface SearchBarProps {
  value: string;
  onSearch: (value: string) => void;
}

/** Search box that commits to the URL 300 ms after typing stops. */
export function SearchBar({ value, onSearch }: SearchBarProps) {
  // Follows external changes too (back button, "clear filters").
  const [text, setText] = useSyncedState(value);
  const debounced = useDebouncedValue(text, 300);
  const lastDebounced = useRef(debounced);

  // Commit only when the *typed* text settles, never because the URL changed; otherwise
  // clearing filters would race with the stale debounced text and restore the old query.
  useEffect(() => {
    if (debounced === lastDebounced.current) return;
    lastDebounced.current = debounced;
    if (debounced.trim() !== value) onSearch(debounced.trim());
  }, [debounced, value, onSearch]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch(text.trim());
  };

  return (
    <form className={styles.search} role="search" onSubmit={submit}>
      <label htmlFor="job-search" className="visually-hidden">
        Search jobs
      </label>
      <svg className={styles.icon} viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
        <path
          d="m13.2 13.2 3.6 3.6"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
      <input
        id="job-search"
        type="search"
        className={styles.input}
        placeholder="Barista, data analyst, tutor, Manchester…"
        value={text}
        onChange={(event) => setText(event.target.value)}
        autoComplete="off"
      />
    </form>
  );
}
