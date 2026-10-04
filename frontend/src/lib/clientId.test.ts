import { describe, expect, it, vi } from "vitest";

import { getClientId } from "./clientId";

describe("getClientId", () => {
  it("creates one id per browser and keeps it", () => {
    const first = getClientId();

    expect(first).toMatch(/^[0-9a-f-]{36}$/);
    expect(getClientId()).toBe(first);
    expect(window.localStorage.getItem("gradguide.client-id")).toBe(first);
  });

  it("replaces a tampered value", () => {
    window.localStorage.setItem("gradguide.client-id", "not valid!");
    expect(getClientId()).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("still works when storage is blocked", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    const id = getClientId();

    expect(id).toMatch(/^[0-9a-f-]{36}$/);
    expect(getClientId()).toBe(id); // stable for the session
  });
});
