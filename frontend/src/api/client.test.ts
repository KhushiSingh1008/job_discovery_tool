import { describe, expect, it } from "vitest";

import { jsonError, mockApi } from "../test/mockApi";
import { ApiError, request, toQueryString } from "./client";

describe("toQueryString", () => {
  it("skips empty values and repeats array keys", () => {
    expect(
      toQueryString({ q: "barista", page: 2, job_type: ["part-time", "internship"], x: "" }),
    ).toBe("?q=barista&page=2&job_type=part-time&job_type=internship");
    expect(toQueryString({ a: undefined, b: null })).toBe("");
  });
});

describe("request", () => {
  it("returns parsed JSON", async () => {
    mockApi({ "GET /api/health": () => ({ status: "ok" }) });
    await expect(request("/api/health")).resolves.toEqual({ status: "ok" });
  });

  it("raises ApiError with the server's detail message", async () => {
    mockApi({ "POST /api/applications": () => jsonError(409, "Already tracked") });

    const error: unknown = await request("/api/applications", { method: "POST" }).catch(
      (e: unknown) => e,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, message: "Already tracked" });
  });

  it("turns validation errors into a readable message", async () => {
    mockApi({
      "POST /api/match": () =>
        new Response(JSON.stringify({ detail: [{ loc: ["body"], msg: "x" }] }), { status: 422 }),
    });
    await expect(request("/api/match", { method: "POST" })).rejects.toThrow(
      "Some of the details you entered are not valid.",
    );
  });

  it("identifies this browser so the tracker stays private", async () => {
    const { fetchMock } = mockApi({ "GET /api/applications": () => [] });

    await request("/api/applications");

    const headers = fetchMock.mock.calls[0]![1]!.headers as Record<string, string>;
    expect(headers["X-Client-Id"]).toBe(window.localStorage.getItem("gradguide.client-id"));
  });

  it("returns undefined for 204 No Content", async () => {
    mockApi({ "DELETE /api/applications/1": () => undefined });
    await expect(request("/api/applications/1", { method: "DELETE" })).resolves.toBeUndefined();
  });
});
