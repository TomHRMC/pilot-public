/**
 * useMoveJob unit tests — DISPATCH-B1
 *
 * Tests:
 *   - fires POST /scheduling/jobs/:id/move with correct body incl. expected_job_version
 *   - mutationKey is ["moveJob"]
 */

import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useMoveJob } from "../useMoveJob";

// ── MSW server ────────────────────────────────────────────────────────────────

let capturedBody: Record<string, unknown> | null = null;
let capturedJobId = "";

const server = setupServer(
  http.post<{ id: string }>(
    "/api/v1/scheduling/jobs/:id/move",
    async ({ request, params }) => {
      capturedJobId = params.id;
      capturedBody = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        job_id: params.id,
        job_version: ((capturedBody?.expected_job_version as number) ?? 1) + 1,
        assignment_id: "assign-001",
        assignment_version: 3,
        tech_user_id: capturedBody?.tech_user_id,
        scheduled_start_at: capturedBody?.scheduled_start_at,
        scheduled_end_at: capturedBody?.scheduled_end_at,
        conflicts: [],
      });
    },
  ),
  // Board query used by useMoveJob optimistic update
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json({ techs: [], unassigned: [], jobs: [] }),
  ),
  // Subscription tiers
  http.get("/api/v1/subscription-tiers/", () =>
    HttpResponse.json({ tiers: [{ tier_id: "t1", schedule_lanes: 5 }] }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedBody = null;
  capturedJobId = "";
});
afterAll(() => server.close());

// ── Wrapper ───────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  }
  Wrapper.displayName = "TestWrapper";
  return Wrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useMoveJob", () => {
  it("fires POST /api/v1/scheduling/jobs/:id/move with correct body including expected_job_version", async () => {
    const { result } = renderHook(
      () => useMoveJob("2026-07-28", "2026-07-28"),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.moveJob({
        jobId: "job-b30-001",
        tech_user_id: "tech-00000001",
        scheduled_start_at: "2026-07-28T09:00:00.000Z",
        scheduled_end_at: "2026-07-28T12:00:00.000Z",
        expected_job_version: 3,
        expected_assignment_version: 2,
      });
    });

    await waitFor(() => expect(result.current.isPending).toBe(false));

    expect(capturedJobId).toBe("job-b30-001");
    expect(capturedBody).toMatchObject({
      tech_user_id: "tech-00000001",
      scheduled_start_at: "2026-07-28T09:00:00.000Z",
      scheduled_end_at: "2026-07-28T12:00:00.000Z",
      expected_job_version: 3,
      expected_assignment_version: 2,
    });
  });

  it("omits expected_assignment_version when not provided", async () => {
    const { result } = renderHook(
      () => useMoveJob("2026-07-28", "2026-07-28"),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.moveJob({
        jobId: "job-b30-001",
        tech_user_id: "tech-00000001",
        scheduled_start_at: "2026-07-28T09:00:00.000Z",
        scheduled_end_at: "2026-07-28T12:00:00.000Z",
        expected_job_version: 1,
      });
    });

    await waitFor(() => expect(result.current.isPending).toBe(false));

    expect(capturedBody).not.toHaveProperty("expected_assignment_version");
  });

  it("exposes StalenessDialog for staleness retry UI", () => {
    const { result } = renderHook(
      () => useMoveJob("2026-07-28", "2026-07-28"),
      { wrapper: createWrapper() },
    );

    expect(typeof result.current.StalenessDialog).toBe("function");
    expect(typeof result.current.moveJob).toBe("function");
  });

  it("handles 409 staleness response without crashing", async () => {
    server.use(
      http.post<{ id: string }>(
        "/api/v1/scheduling/jobs/:id/move",
        async () => {
          return HttpResponse.json(
            {
              type: "https://errors.pilotfortrades.com/staleness",
              title: "Job was updated",
              status: 409,
              current_job_version: 5,
              current_state: {
                scheduled_start_at: "2026-07-28T10:00:00.000Z",
                scheduled_end_at: "2026-07-28T13:00:00.000Z",
              },
            },
            { status: 409 },
          );
        },
      ),
    );

    const { result } = renderHook(
      () => useMoveJob("2026-07-28", "2026-07-28"),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.moveJob({
        jobId: "job-b30-001",
        tech_user_id: "tech-00000001",
        scheduled_start_at: "2026-07-28T09:00:00.000Z",
        scheduled_end_at: "2026-07-28T12:00:00.000Z",
        expected_job_version: 3,
      });
    });

    // Wait for mutation to settle (either pending or dialog opened)
    await waitFor(
      () =>
        result.current.isPending === false ||
        result.current.isStalenessDialogOpen === true,
    );

    // The mutation handles 409 gracefully via useStalenessRetry
    expect(
      result.current.isError || result.current.isStalenessDialogOpen,
    ).toBeTruthy();
  });
});
