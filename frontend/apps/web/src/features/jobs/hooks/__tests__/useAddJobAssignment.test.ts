/**
 * useAddJobAssignment unit tests — UI-FIX-2B
 *
 * Location: apps/web/src/features/jobs/hooks/__tests__/useAddJobAssignment.test.ts
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";

import { useAddJobAssignment } from "../useAddJobAssignment";

let lastPostBody: unknown = null;

const server = setupServer(
  http.get("/api/v1/scheduling/jobs/:jobId/assignments", () => {
    return HttpResponse.json([]);
  }),
  http.post(
    "/api/v1/scheduling/jobs/:jobId/assignments",
    async ({ params, request }) => {
      const { jobId } = params as { jobId: string };
      lastPostBody = await request.json();
      return HttpResponse.json(
        {
          id: "assign-new",
          job_id: jobId,
          ...(lastPostBody as object),
          is_active: true,
          assigned_at: new Date().toISOString(),
        },
        { status: 201 },
      );
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  lastPostBody = null;
});
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

describe("useAddJobAssignment", () => {
  it("fires POST with the correct body including user_id and role", async () => {
    const { result } = renderHook(() => useAddJobAssignment("job-001"), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        user_id: "user-002",
        role: "primary",
      });
    });

    expect(lastPostBody).toMatchObject({
      user_id: "user-002",
      role: "primary",
    });
  });

  it("returns the newly created assignment on success", async () => {
    const { result } = renderHook(() => useAddJobAssignment("job-001"), {
      wrapper: createWrapper(),
    });

    let response: unknown;
    await act(async () => {
      response = await result.current.mutateAsync({
        user_id: "user-003",
        role: "helper",
      });
    });

    expect((response as { id: string }).id).toBe("assign-new");
    expect((response as { user_id: string }).user_id).toBe("user-003");
  });

  it("invalidates job-assignments query key on success", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children,
      );

    const { result } = renderHook(() => useAddJobAssignment("job-001"), {
      wrapper,
    });

    await act(async () => {
      await result.current.mutateAsync({
        user_id: "user-002",
        role: "primary",
      });
    });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ["job-assignments", "job-001"],
        }),
      );
    });
  });
});
