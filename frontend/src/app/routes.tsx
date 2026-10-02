import type { RouteObject } from "react-router";

import { AppLayout } from "../components/layout/AppLayout";
import { JobDetailPage } from "../pages/JobDetailPage";
import { JobsPage } from "../pages/JobsPage";
import { MatchPage } from "../pages/MatchPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { TrackerPage } from "../pages/TrackerPage";

export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <JobsPage /> },
      { path: "jobs/:listingId", element: <JobDetailPage /> },
      { path: "tracker", element: <TrackerPage /> },
      { path: "match", element: <MatchPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
