import { useCallback, useSyncExternalStore } from "react";

/** Live result of a CSS media query (false where ``matchMedia`` is unavailable). */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = window.matchMedia?.(query);
      list?.addEventListener("change", onChange);
      return () => list?.removeEventListener("change", onChange);
    },
    [query],
  );
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia?.(query).matches ?? false,
    () => false,
  );
}

/** The split list/detail layout is used from this width up. */
export const SPLIT_VIEW_QUERY = "(min-width: 1024px)";
