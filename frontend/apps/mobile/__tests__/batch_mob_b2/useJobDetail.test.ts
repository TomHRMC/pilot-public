/**
 * useJobDetail unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/useJobDetail.test.ts
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

// ── Mocks ──────────────────────────────────────────────────────────────────────

const MOCK_USER_ID = "tech-user-001";
const MOCK_JOB_ID = "job-today-001";
const TODAY = new Date().toISOString().slice(0, 10);

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: MOCK_USER_ID },
  }),
}));

// ── Server ─────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId", () => {
    return HttpResponse.json({
      id: MOCK_JOB_ID,
      tenant_id: "tenant-001",
      customer_id: "customer-001",
      site_id: "site-001",
      status_id: "status-scheduled",
      scheduled_start_at: `${TODAY}T09:00:00Z`,
      scheduled_end_at: `${TODAY}T12:00:00Z`,
      estimated_duration_minutes: 180,
    });
  }),
  http.get("*/api/v1/jobs/:jobId/time-entries", () => {
    return HttpResponse.json([
      {
        id: "te-001",
        job_id: MOCK_JOB_ID,
        user_id: MOCK_USER_ID,
        started_at: `${TODAY}T09:00:00Z`,
        ended_at: null,
        hours: null,
        notes: null,
        hourly_rate_cents: 8500,
      },
    ]);
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

// ── Tests ──────────────────────────────────────────────────────────────────────

import { useJobDetail } from "../../features/jobs/hooks/useJobDetail";

describe("useJobDetail", () => {
  it("calls GET /api/v1/jobs/{id} and /api/v1/jobs/{id}/time-entries", async () => {
    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.job.id).toBe(MOCK_JOB_ID);
    expect(result.current.data?.timeEntries).toHaveLength(1);
  });

  it("derives activeTimeEntry from open entry with matching user_id", async () => {
    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.activeTimeEntry).not.toBeNull();
    expect(result.current.data?.activeTimeEntry?.ended_at).toBeNull();
    expect(result.current.data?.activeTimeEntry?.user_id).toBe(MOCK_USER_ID);
  });

  it("returns null activeTimeEntry when all entries have ended_at set", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId/time-entries", () => {
        return HttpResponse.json([
          {
            id: "te-001",
            job_id: MOCK_JOB_ID,
            user_id: MOCK_USER_ID,
            started_at: `${TODAY}T09:00:00Z`,
            ended_at: `${TODAY}T11:00:00Z`,
            hours: 2,
            notes: null,
            hourly_rate_cents: 8500,
          },
        ]);
      }),
    );

    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.activeTimeEntry).toBeNull();
  });

  it("returns null activeTimeEntry for entry belonging to different user", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId/time-entries", () => {
        return HttpResponse.json([
          {
            id: "te-001",
            job_id: MOCK_JOB_ID,
            user_id: "other-user-999",
            started_at: `${TODAY}T09:00:00Z`,
            ended_at: null,
            hours: null,
            notes: null,
            hourly_rate_cents: 8500,
          },
        ]);
      }),
    );

    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.activeTimeEntry).toBeNull();
  });

  it("returns null status_code when cache is empty (direct navigation)", async () => {
    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    // No MOB-B1 cache populated in this test → null
    expect(result.current.data?.status_code).toBeNull();
  });

  it("resolves status_code from TanStack Query cache when populated", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    // Pre-populate the MOB-B1 cache
    queryClient.setQueryData(
      ["tech-jobs-today", MOCK_USER_ID, TODAY],
      [
        {
          id: MOCK_JOB_ID,
          status_code: "scheduled",
          customer_name: "Acme Electric",
          tenant_id: "tenant-001",
          customer_id: "customer-001",
          site_id: "site-001",
          status_id: "status-scheduled",
        },
      ],
    );

    const wrp = ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children,
      );

    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), {
      wrapper: wrp,
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.status_code).toBe("scheduled");
    expect(result.current.data?.customer_name).toBe("Acme Electric");
  });

  it("sets isError when job fetch returns 500", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId", () => {
        return HttpResponse.json({ detail: "error" }, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useJobDetail(MOCK_JOB_ID), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
  });
});
