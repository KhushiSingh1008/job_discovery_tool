import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useSyncedState } from "./useSyncedState";

describe("useSyncedState", () => {
  it("keeps local edits until the source changes", () => {
    const { result, rerender } = renderHook(({ source }) => useSyncedState(source), {
      initialProps: { source: "8" },
    });

    act(() => result.current[1]("10"));
    expect(result.current[0]).toBe("10");

    rerender({ source: "8" }); // same source: the edit survives
    expect(result.current[0]).toBe("10");

    rerender({ source: "12" }); // new source (e.g. saved on the server): reset
    expect(result.current[0]).toBe("12");
  });
});
