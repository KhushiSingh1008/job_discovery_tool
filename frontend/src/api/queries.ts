import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./endpoints";
import type { ApplicationCreate, ApplicationUpdate, ListingQuery, VisaSettings } from "./types";

/** One place for cache keys, so invalidation can target whole families of queries. */
export const queryKeys = {
  listings: (query: ListingQuery) => ["listings", query] as const,
  listing: (id: string) => ["listing", id] as const,
  facets: ["facets"] as const,
  visaRules: ["visa-rules"] as const,
  applications: ["applications"] as const,
  hoursSummary: (settings: VisaSettings) => ["applications", "hours", settings] as const,
  reminders: ["applications", "reminders"] as const,
};

const STATIC_DATA_MS = 10 * 60 * 1000;

export function useListings(query: ListingQuery) {
  return useQuery({
    queryKey: queryKeys.listings(query),
    queryFn: () => api.listings(query),
    placeholderData: keepPreviousData, // keep showing results while the next page loads
  });
}

export function useListing(id: string) {
  return useQuery({ queryKey: queryKeys.listing(id), queryFn: () => api.listing(id) });
}

export function useFacets() {
  return useQuery({ queryKey: queryKeys.facets, queryFn: api.facets, staleTime: STATIC_DATA_MS });
}

export function useVisaRules() {
  return useQuery({
    queryKey: queryKeys.visaRules,
    queryFn: api.visaRules,
    staleTime: Infinity,
  });
}

export function useApplications() {
  return useQuery({ queryKey: queryKeys.applications, queryFn: api.applications });
}

export function useHoursSummary(settings: VisaSettings) {
  return useQuery({
    queryKey: queryKeys.hoursSummary(settings),
    queryFn: () => api.hoursSummary(settings),
    placeholderData: keepPreviousData,
  });
}

export function useReminders() {
  return useQuery({ queryKey: queryKeys.reminders, queryFn: api.reminders });
}

/** Every tracker mutation refreshes the board, the hours guard and the reminders. */
function useInvalidateTracker() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: queryKeys.applications });
}

export function useTrackJob() {
  const invalidate = useInvalidateTracker();
  return useMutation({
    mutationFn: (data: ApplicationCreate) => api.createApplication(data),
    onSuccess: invalidate,
  });
}

export function useUpdateApplication() {
  const invalidate = useInvalidateTracker();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ApplicationUpdate }) =>
      api.updateApplication(id, data),
    onSuccess: invalidate,
  });
}

export function useDeleteApplication() {
  const invalidate = useInvalidateTracker();
  return useMutation({
    mutationFn: (id: number) => api.deleteApplication(id),
    onSuccess: invalidate,
  });
}

export function useMatch() {
  return useMutation({ mutationFn: api.match });
}
