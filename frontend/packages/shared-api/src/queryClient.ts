/**
 * QueryClient Factory — shared TanStack Query client
 *
 * Location: packages/shared-api/src/queryClient.ts
 *
 * Usage: All <QueryClientProvider> instances must use this factory
 * to ensure consistent defaults across web and mobile.
 *
 * Defaults per methods doc §4.1:
 *   - staleTime: 5 minutes (300,000ms)
 *   - retry: 1 for queries, 0 for mutations
 *   - refetchOnWindowFocus: true
 */

import { QueryClient } from "@tanstack/react-query";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes — per methods doc §4.1
        retry: 1,
        refetchOnWindowFocus: true,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
