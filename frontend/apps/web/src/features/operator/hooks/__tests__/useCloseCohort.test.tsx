/**
 * useCloseCohort unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/features/operator/hooks/__tests__/useCloseCohort.test.tsx
 *
 * Tests: mutation fires correct POST, invalidates cohort query.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useCloseCohort } from "../useCloseCohort";
import { COHORT_OVERVIEW_QUERY_KEY } from "../useCohortOverview";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

describe("useCloseCohort (web)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fires POST /api/v1/operator/cohort/close", async () => {
    server.use(
      http.post("/api/v1/operator/cohort/close", () =>
        HttpResponse.json({
          charter_price_archived: true,
          charter_tier_deactivated: true,
          activated_tiers: ["trial", "starter", "teams"],
        }),
      ),
    );

    const { result } = renderHook(() => useCloseCohort(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.charter_price_archived).toBe(true);
    expect(result.current.data?.charter_tier_deactivated).toBe(true);
    expect(result.current.data?.activated_tiers).toEqual([
      "trial",
      "starter",
      "teams",
    ]);
  });

  it("invalidates the cohort overview query on success", async () => {
    server.use(
      http.post("/api/v1/operator/cohort/close", () =>
        HttpResponse.json({
          charter_price_archived: true,
          charter_tier_deactivated: true,
          activated_tiers: ["trial", "starter", "teams"],
        }),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi
      .spyOn(queryClient, "invalidateQueries")
      .mockImplementation(() => Promise.resolve());

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useCloseCohort(), {
      wrapper: Wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: COHORT_OVERVIEW_QUERY_KEY,
    });

    invalidateSpy.mockRestore();
  });
});
