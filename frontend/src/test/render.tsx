import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";

import { Providers } from "../app/providers";
import { createQueryClient } from "../app/queryClient";

/** Render routes in memory with fresh providers (no retries, no shared cache). */
export function renderRoutes(routes: RouteObject[], initialPath = "/") {
  const router = createMemoryRouter(routes, { initialEntries: [initialPath] });
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { retry: false, staleTime: 0 } });
  const utils = render(
    <Providers client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { ...utils, router, client };
}

/** Render a single element inside a router at ``path``. */
export function renderWithProviders(element: ReactElement, path = "/") {
  return renderRoutes([{ path: "*", element }], path);
}

/** Pretend to be a wide screen, so the jobs page shows the list/detail split view. */
export function mockWideScreen() {
  vi.spyOn(window, "matchMedia").mockImplementation((query: string) => ({
    matches: true,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
  }));
}
