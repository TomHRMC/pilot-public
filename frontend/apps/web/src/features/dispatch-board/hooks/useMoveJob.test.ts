/**
 * useMoveJob — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useMoveJob.test.ts
 *
 * DISPATCH-B1 update: rewrote all tests to the new /scheduling/jobs/{id}/move
 * contract. The old /reschedule + /assign split has been replaced by a single
 * atomic /move endpoint.
 *
 * Per DISPATCH-B1 design doc §D.2
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const MOCK_MOVE_RESPONSE = {
  job_id: "job-1",
  job_version: 4,
  assignment_id: "assign-001",
  assignment_version: 3,
  tech_user_id: "tech-1",
  scheduled_start_at: "2026-06-10T10:00:00Z",
  scheduled_end_at: "2026-06-10T12:00:00Z",
  conflicts: [],
};

const server = setupServer(
  http.post(
    "/api/v1/scheduling/jobs/:jobId/move",
    async ({ request, params }) => {
      const body = await request.json();
      return HttpResponse.json({
        ...MOCK_MOVE_RESPONSE,
        job_id: params.jobId as string,
        _req: body,
      });
    },
  ),
  // Board query used by optimistic update
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json({ techs: [], unassigned: [], jobs: [] }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
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

describe("useMoveJob", () => {
  it("includes expected_job_version in request body", async () => {
    const { useMoveJob } = await import("./useMoveJob");

    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/scheduling/jobs/:jobId/move", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(MOCK_MOVE_RESPONSE);
      }),
    );

    const { result } = renderHook(
      () => useMoveJob("2026-06-10", "2026-06-10"),
      { wrapper: makeWrapper() },
    );

    act(() => {
      result.current.moveJob({
        jobId: "job-1",
        tech_user_id: "tech-1",
        scheduled_start_at: "2026-06-10T10:00:00Z",
        scheduled_end_at: "2026-06-10T12:00:00Z",
        expected_job_version: 3,
      });
    });

    await waitFor(() => capturedBody !== null);

    expect(capturedBody).toHaveProperty("expected_job_version", 3);
  });

  it("uses /scheduling/jobs/:id/move endpoint", async () => {
    const { useMoveJob } = await import("./useMoveJob");

    let capturedUrl = "";
    server.use(
      http.post("/api/v1/scheduling/jobs/:jobId/move", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(MOCK_MOVE_RESPONSE);
      }),
    );

    const { result } = renderHook(
      () => useMoveJob("2026-06-10", "2026-06-10"),
      { wrapper: makeWrapper() },
    );

    act(() => {
      result.current.moveJob({
        jobId: "job-1",
        tech_user_id: "tech-1",
        scheduled_start_at: "2026-06-10T10:00:00Z",
        scheduled_end_at: "2026-06-10T12:00:00Z",
        expected_job_version: 1,
      });
    });

    await waitFor(() => capturedUrl !== "");
    expect(capturedUrl).toContain("/scheduling/jobs/");
    expect(capturedUrl).toContain("/move");
  });

  it("sends tech_user_id (not tech_id) in request body", async () => {
    const { useMoveJob } = await import("./useMoveJob");

    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/scheduling/jobs/:jobId/move", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(MOCK_MOVE_RESPONSE);
      }),
    );

    const { result } = renderHook(
      () => useMoveJob("2026-06-10", "2026-06-10"),
      { wrapper: makeWrapper() },
    );

    act(() => {
      result.current.moveJob({
        jobId: "job-1",
        tech_user_id: "tech-2",
        scheduled_start_at: "2026-06-10T10:00:00Z",
        scheduled_end_at: "2026-06-10T12:00:00Z",
        expected_job_version: 1,
      });
    });

    await waitFor(() => capturedBody !== null);
    expect(capturedBody).toHaveProperty("tech_user_id", "tech-2");
    expect(capturedBody).not.toHaveProperty("tech_id");
  });

  it("exposes StalenessDialog component", async () => {
    const { useMoveJob } = await import("./useMoveJob");

    const { result } = renderHook(
      () => useMoveJob("2026-06-10", "2026-06-10"),
      { wrapper: makeWrapper() },
    );

    expect(result.current.StalenessDialog).toBeTypeOf("function");
  });

  it("isPending is false initially", async () => {
    const { useMoveJob } = await import("./useMoveJob");

    const { result } = renderHook(
      () => useMoveJob("2026-06-10", "2026-06-10"),
      { wrapper: makeWrapper() },
    );

    expect(result.current.isPending).toBe(false);
  });
});
