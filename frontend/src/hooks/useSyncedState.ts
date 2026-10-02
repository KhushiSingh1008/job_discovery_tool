import { useState, type Dispatch, type SetStateAction } from "react";

/**
 * Local, editable state that resets whenever ``source`` changes (e.g. an input showing a
 * server value). Adjusting state during render is React's recommended alternative to a
 * syncing effect: it avoids an extra render with stale data.
 * https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
 */
export function useSyncedState<T>(source: T): [T, Dispatch<SetStateAction<T>>] {
  const [state, setState] = useState(source);
  const [syncedFrom, setSyncedFrom] = useState(source);
  if (!Object.is(syncedFrom, source)) {
    setSyncedFrom(source);
    setState(source);
  }
  return [state, setState];
}
