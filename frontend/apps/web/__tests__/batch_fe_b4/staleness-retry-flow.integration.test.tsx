/**
 * Staleness Retry Flow — Integration Tests
 *
 * Location: apps/web/__tests__/batch_fe_b4/staleness-retry-flow.integration.test.tsx
 * Per batch-fe-b4-design.md §I.2
 * Target: 3 tests
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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { renderHook, act } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { StalenessRefreshDialog, useStalenessRetry } from "@pilot/ui";

const stalenessHandlers = [
  http.post<{ id: string }>(
    "/api/v1/schedule/jobs/:id/reschedule",
    async ({ request }) => {
      const body = (await request.json()) as { expected_updated_at: string };
      if (body.expected_updated_at === "stale-version") {
        return HttpResponse.json(
          {
            status: 409,
            title: "Record updated since last view",
            detail: "The job was moved since you loaded the board.",
            refreshed_state: {
              id: "job-1",
              tech_id: "tech-2",
              scheduled_start_at: new Date().toISOString(),
              scheduled_end_at: new Date().toISOString(),
              updated_at: "2026-06-10T10:00:00Z",
              tech_name: "Sarah Kim",
            },
          },
          { status: 409 },
        );
      }
      return HttpResponse.json({
        id: "job-1",
        tech_id: "tech-1",
        scheduled_start_at: new Date().toISOString(),
        scheduled_end_at: new Date().toISOString(),
        updated_at: "2026-06-10T10:01:00Z",
      });
    },
  ),
];

const server = setupServer(...stalenessHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("Staleness Retry Flow — Integration", () => {
  it("useStalenessRetry opens dialog on 409 when no onConflict", async () => {
    // Test useStalenessRetry directly with a 409-returning fn
    const mutationFn = vi.fn().mockRejectedValue(
      Object.assign(new Error("Stale"), {
        status: 409,
        data: {
          status: 409,
          title: "Record updated",
          detail: "The job was moved",
          refreshed_state: {
            id: "job-1",
            tech_id: "tech-2",
            updated_at: "2026-06-10T10:01:00Z",
          },
        },
      }),
    );

    const { result } = renderHook(
      () =>
        useStalenessRetry<
          { jobId: string; expected_updated_at: string },
          { id: string },
          { id: string; tech_id: string; updated_at: string }
        >({ mutationFn }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "job-1",
        expected_updated_at: "stale-version",
      }),
    );

    await waitFor(() =>
      expect(result.current.isStalenessDialogOpen).toBe(true),
    );
  });

  it("StalenessRefreshDialog Retry button fires onRetry callback", async () => {
    const onRetry = vi.fn();
    const onCancel = vi.fn();

    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={onRetry}
        onCancel={onCancel}
      />,
    );

    await waitFor(() =>
      expect(screen.getByText("Retry with updated data")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("Retry with updated data"));
    expect(onRetry).toHaveBeenCalled();
  });

  it("StalenessRefreshDialog Cancel calls onCancel", async () => {
    const onRetry = vi.fn();
    const onCancel = vi.fn();

    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={onRetry}
        onCancel={onCancel}
      />,
    );

    await waitFor(() => expect(screen.getByText("Cancel")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalled();
  });
});
