import { useCallback, useState } from "react";

function read<T>(key: string, fallback: T): T {
  try {
    const stored = window.localStorage.getItem(key);
    return stored === null ? fallback : (JSON.parse(stored) as T);
  } catch {
    return fallback; // private mode, blocked storage or corrupted JSON
  }
}

/** State persisted per browser. Storage failures never break the page. */
export function useLocalStorage<T>(key: string, fallback: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => read(key, fallback));

  const update = useCallback(
    (next: T) => {
      setValue(next);
      try {
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch {
        // Ignore: the value still lives in memory for this session.
      }
    },
    [key],
  );

  return [value, update];
}
