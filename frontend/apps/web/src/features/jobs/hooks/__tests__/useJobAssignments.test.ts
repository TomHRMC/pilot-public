/**
 * useJobAssignments unit tests — UI-FIX-2B
 *
 * Location: apps/web/src/features/jobs/hooks/__tests__/useJobAssignments.test.ts
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";

import { useJobAssignments } from "../useJobAssignments";

const MOCK_ASSIGNMENTS = [
  {
    id: "assign-001",
    job_id: "job-abc",
    user_id: "user-002",
    role: "primary",
    ordinal: 1,
    assigned_at: "2026-07-21T10:00:00Z",
    is_active: true,
  },
];

const server = setupServer(
  http.get("/api/v1/scheduling/jobs/:jobId/assignments", ({ params }) => {
    const { jobId } = params as { jobId: string };
    if (jobId === "job-abc") {
      return HttpResponse.json(MOCK_ASSIGNMENTS);
    }
    return HttpResponse.json([]);
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

describe("useJobAssignments", () => {
  it("calls the correct endpoint with jobId", async () => {
    const { result } = renderHook(() => useJobAssignments("job-abc"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data![0].id).toBe("assign-001");
  });

  it("returns data from API including role field", async () => {
    const { result } = renderHook(() => useJobAssignments("job-abc"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const assignment = result.current.data![0];
    expect(assignment.role).toBe("primary");
    expect(assignment.user_id).toBe("user-002");
    expect(assignment.job_id).toBe("job-abc");
  });

  it("is disabled when jobId is undefined", async () => {
    const { result } = renderHook(() => useJobAssignments(undefined), {
      wrapper: createWrapper(),
    });
    // Should stay in idle/pending with no fetch
    expect(result.current.isFetching).toBe(false);
    expect(result.current.data).toBeUndefined();
  });
});
