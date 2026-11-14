/**
 * useExtendFreePeriod unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/features/operator/hooks/__tests__/useExtendFreePeriod.test.tsx
 *
 * Tests: mutation fires correct POST, invalidates cohort query, error handling.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useExtendFreePeriod } from "../useExtendFreePeriod";
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

describe("useExtendFreePeriod (web)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fires POST /api/v1/operator/cohort/:tenantId/extend with correct body", async () => {
    let capturedBody: unknown = null;
    server.use(
      http.post(
        "/api/v1/operator/cohort/:tenantId/extend",
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            tenant_id: "tenant-001",
            previous_free_period_ends_at: "2026-11-04T00:00:00Z",
            new_free_period_ends_at: "2026-12-04T00:00:00Z",
            stripe_subscription_id: "sub_mock_001",
            stripe_trial_end_updated: true,
          });
        },
      ),
    );

    const { result } = renderHook(() => useExtendFreePeriod(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      tenantId: "tenant-001",
      newFreePeriodEndsAt: "2026-12-04T00:00:00Z",
      overrideReason: "Customer needs more time to evaluate",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(capturedBody).toEqual({
      new_free_period_ends_at: "2026-12-04T00:00:00Z",
      override_reason: "Customer needs more time to evaluate",
    });
    expect(result.current.data?.stripe_trial_end_updated).toBe(true);
  });

  it("invalidates the cohort overview query on success", async () => {
    const invalidateSpy = vi.fn();
    server.use(
      http.post("/api/v1/operator/cohort/:tenantId/extend", () =>
        HttpResponse.json({
          tenant_id: "tenant-001",
          previous_free_period_ends_at: "2026-11-04T00:00:00Z",
          new_free_period_ends_at: "2026-12-04T00:00:00Z",
          stripe_subscription_id: "sub_mock_001",
          stripe_trial_end_updated: true,
        }),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpyWrapped = vi
      .spyOn(queryClient, "invalidateQueries")
      .mockImplementation(invalidateSpy);

    function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useExtendFreePeriod(), {
      wrapper: Wrapper,
    });

    result.current.mutate({
      tenantId: "tenant-001",
      newFreePeriodEndsAt: "2026-12-04T00:00:00Z",
      overrideReason: "Customer needs more time to evaluate",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpyWrapped).toHaveBeenCalledWith({
      queryKey: COHORT_OVERVIEW_QUERY_KEY,
    });

    invalidateSpyWrapped.mockRestore();
  });

  it("handles 409 error (not trialing)", async () => {
    server.use(
      http.post("/api/v1/operator/cohort/:tenantId/extend", () =>
        HttpResponse.json(
          { detail: "Subscription is not trialing" },
          { status: 409 },
        ),
      ),
    );

    const { result } = renderHook(() => useExtendFreePeriod(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      tenantId: "tenant-001",
      newFreePeriodEndsAt: "2026-12-04T00:00:00Z",
      overrideReason: "Customer needs more time to evaluate",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.data).toBeUndefined();
  });
});
