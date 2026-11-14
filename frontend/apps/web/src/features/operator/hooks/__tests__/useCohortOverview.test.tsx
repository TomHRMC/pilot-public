/**
 * useCohortOverview unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/features/operator/hooks/__tests__/useCohortOverview.test.tsx
 *
 * Tests: returns data shape, error state, query key.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import {
  useCohortOverview,
  COHORT_OVERVIEW_QUERY_KEY,
} from "../useCohortOverview";

const mockCohortOverview = {
  cohort_tier_name: "Charter",
  cohort_is_active: true,
  signup_cap: 12,
  members: [
    {
      tenant_id: "tenant-001",
      business_name: "Acme Electric",
      charter_member_number: 1,
      free_period_ends_at: "2026-11-04T00:00:00Z",
      days_remaining: 90,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "not_started",
      customer_count: 3,
      invoice_count: 2,
      days_since_last_job: 5,
      last_contact: null,
      alert_level: "none",
    },
  ],
};

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

describe("useCohortOverview (web)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns cohort overview data in the expected shape", async () => {
    server.use(
      http.get("/api/v1/operator/cohort", () =>
        HttpResponse.json(mockCohortOverview),
      ),
    );

    const { result } = renderHook(() => useCohortOverview(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.cohort_tier_name).toBe("Charter");
    expect(result.current.data?.cohort_is_active).toBe(true);
    expect(result.current.data?.signup_cap).toBe(12);
    expect(result.current.data?.members).toHaveLength(1);
    expect(result.current.data?.members[0].business_name).toBe("Acme Electric");
    expect(result.current.data?.members[0].alert_level).toBe("none");
  });

  it("returns error state when the API fails", async () => {
    server.use(
      http.get("/api/v1/operator/cohort", () =>
        HttpResponse.json({ detail: "server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useCohortOverview(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.data).toBeUndefined();
  });

  it("uses the correct query key", () => {
    expect(COHORT_OVERVIEW_QUERY_KEY).toEqual(["operator", "cohort"]);
  });
});
