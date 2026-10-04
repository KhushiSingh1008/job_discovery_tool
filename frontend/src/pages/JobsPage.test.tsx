import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { routes } from "../app/routes";
import { EMPTY_FACETS, HOURS_OK, makeListing, mockApi } from "../test/mockApi";
import { mockWideScreen, renderRoutes } from "../test/render";

const LISTINGS = [
  makeListing(),
  makeListing({ id: "intern-1", title: "Summer Software Intern", job_type: "internship" }),
];

const detailFor = (id: string) => ({
  ...LISTINGS.find((listing) => listing.id === id)!,
  description: `Description of ${id}.`,
  first_seen: "2026-09-30T09:00:00Z",
  last_seen: "2026-10-02T09:00:00Z",
  trust_flags: [],
});

function setup(path = "/") {
  const api = mockApi({
    "GET /api/listings": (url) => {
      const q = url.searchParams.get("q");
      const items = q ? LISTINGS.filter((l) => l.title.toLowerCase().includes(q)) : LISTINGS;
      return { items, total: items.length, page: 1, page_size: 12 };
    },
    "GET /api/listings/barista-1": () => detailFor("barista-1"),
    "GET /api/listings/intern-1": () => detailFor("intern-1"),
    "GET /api/meta/filters": () => EMPTY_FACETS,
    "GET /api/applications": () => [],
    "GET /api/applications/hours-summary": () => HOURS_OK,
  });
  const view = renderRoutes(routes, path);
  return { ...api, ...view, user: userEvent.setup() };
}

const listingCalls = (calls: ReturnType<typeof setup>["calls"]) =>
  calls.filter((call) => call.url.pathname === "/api/listings");

describe("JobsPage", () => {
  it("lists jobs with the count and the hours indicator", async () => {
    setup();

    expect(await screen.findByRole("link", { name: "Weekend Barista" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Summer Software Intern" })).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "strong" })).toBeInTheDocument();
    expect(await screen.findByText("8h of 20h")).toBeInTheDocument();
  });

  it("opens jobs on their own page on phones", async () => {
    setup();
    expect(await screen.findByRole("link", { name: "Weekend Barista" })).toHaveAttribute(
      "href",
      "/jobs/barista-1",
    );
    expect(screen.queryByRole("complementary", { name: "Job details" })).not.toBeInTheDocument();
  });

  it("shows the first job beside the list on wide screens, and the one clicked", async () => {
    mockWideScreen();
    const { user, router } = setup();

    const pane = await screen.findByRole("complementary", { name: "Job details" });
    expect(
      await within(pane).findByRole("heading", { name: "Weekend Barista" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Summer Software Intern" }));

    await waitFor(() => expect(router.state.location.search).toBe("?job=intern-1"));
    expect(
      await within(pane).findByRole("heading", { name: "Summer Software Intern" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Summer Software Intern" })).toHaveAttribute(
      "aria-current",
      "true",
    );
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

  it("searches keyword and location together on submit", async () => {
    const { user, router } = setup();
    await screen.findByRole("link", { name: "Weekend Barista" });

    await user.type(screen.getByRole("combobox", { name: "Location" }), "Leeds");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => expect(router.state.location.search).toBe("?location=Leeds"));
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

  it("applies quick filters to the URL and resets to page 1", async () => {
    const { user, router } = setup("/?page=2");
    const quick = await screen.findByRole("group", { name: "Quick filters" });

    await user.click(within(quick).getByRole("button", { name: /Internship/ }));

    await waitFor(() => expect(router.state.location.search).toBe("?job_type=internship"));
  });

  it("shows a helpful error when the API is down", async () => {
    mockApi({});
    renderRoutes(routes, "/");

    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load jobs");
  });
});
