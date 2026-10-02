import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { routes } from "../app/routes";
import { EMPTY_FACETS, HOURS_OK, makeListing, mockApi } from "../test/mockApi";
import { renderRoutes } from "../test/render";

const LISTINGS = [
  makeListing(),
  makeListing({ id: "intern-1", title: "Summer Software Intern", job_type: "internship" }),
];

function setup(path = "/") {
  const api = mockApi({
    "GET /api/listings": (url) => {
      const q = url.searchParams.get("q");
      const items = q ? LISTINGS.filter((l) => l.title.toLowerCase().includes(q)) : LISTINGS;
      return { items, total: items.length, page: 1, page_size: 12 };
    },
    "GET /api/meta/filters": () => EMPTY_FACETS,
    "GET /api/applications/hours-summary": () => HOURS_OK,
  });
  const view = renderRoutes(routes, path);
  return { ...api, ...view, user: userEvent.setup() };
}

const listingCalls = (calls: ReturnType<typeof setup>["calls"]) =>
  calls.filter((call) => call.url.pathname === "/api/listings");

describe("JobsPage", () => {
  it("lists jobs with the hero stats and the hours indicator", async () => {
    setup();

    expect(await screen.findByRole("link", { name: "Weekend Barista" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Summer Software Intern" })).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "strong" })).toBeInTheDocument();
    expect(await screen.findByText("8h of 20h")).toBeInTheDocument();
  });

  it("searches after typing stops and keeps the query in the URL", async () => {
    const { user, router, calls } = setup();
    await screen.findByRole("link", { name: "Weekend Barista" });

    await user.type(screen.getByRole("searchbox", { name: "Search jobs" }), "intern");

    await waitFor(() => expect(router.state.location.search).toBe("?q=intern"));
    expect(await screen.findByText(/for “intern”/)).toBeInTheDocument();
    // The previous results animate out before the new list renders.
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Weekend Barista" })).not.toBeInTheDocument(),
    );
    expect(listingCalls(calls).at(-1)?.url.searchParams.get("q")).toBe("intern");
  });

  it("clearing filters does not bring back the previous search", async () => {
    const { user, router } = setup("/?q=nothing-matches");

    const clear = await screen.findByRole("button", { name: "Clear search" });
    await user.click(clear);

    await waitFor(() => expect(router.state.location.search).toBe(""));
    // Wait past the 300 ms debounce: a stale debounced value must not re-apply the query.
    await new Promise((resolve) => setTimeout(resolve, 450));
    expect(router.state.location.search).toBe("");
    expect(await screen.findByRole("link", { name: "Weekend Barista" })).toBeInTheDocument();
  });

  it("applies filter changes to the URL and resets to page 1", async () => {
    const { user, router } = setup("/?page=2");
    await screen.findByRole("heading", { name: /Work that fits your/ });

    await user.click(screen.getAllByRole("button", { name: /Internship/ })[0]!);

    await waitFor(() => expect(router.state.location.search).toBe("?job_type=internship"));
  });

  it("shows a helpful error when the API is down", async () => {
    mockApi({});
    renderRoutes(routes, "/");

    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load jobs");
  });
});
