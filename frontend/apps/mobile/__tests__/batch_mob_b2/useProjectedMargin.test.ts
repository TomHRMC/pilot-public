/**
 * useProjectedMargin unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/useProjectedMargin.test.ts
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const MOCK_JOB_ID = "job-today-001";

// ── Mock expo-router useFocusEffect (no-op in tests) ──────────────────────────
// Do NOT call the callback — avoids triggering refetch during render in tests.

jest.mock("expo-router", () => ({
  useFocusEffect: (_cb: () => void) => {
    /* no-op */
  },
}));

// ── Server ─────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId/projected-margin", () => {
    return HttpResponse.json({
      margin_percent: 38,
      quoted_hours: 3,
      actual_hours: 2.5,
      cost_delta_cents: 4200,
      etc_hours_remaining: 0.5,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Wrapper ────────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return React.createElement(
    QueryClientProvider,
    { client: queryClient },
    children,
  );
}

import { useProjectedMargin } from "../../features/jobs/hooks/useProjectedMargin";

describe("useProjectedMargin", () => {
  it("calls GET /api/v1/jobs/{id}/projected-margin and returns data", async () => {
    const { result } = renderHook(() => useProjectedMargin(MOCK_JOB_ID), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.margin_percent).toBe(38);
    expect(result.current.data?.quoted_hours).toBe(3);
    expect(result.current.data?.actual_hours).toBe(2.5);
    expect(result.current.data?.cost_delta_cents).toBe(4200);
  });

  it("sets isError on fetch failure", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId/projected-margin", () => {
        return HttpResponse.json({ detail: "error" }, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useProjectedMargin(MOCK_JOB_ID), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
  });
});
