/**
 * useWipReport — Unit Tests
 *
 * Location: apps/web/src/features/wip/hooks/__tests__/useWipReport.test.ts
 *
 * Verifies:
 * 1. Returns shape with mock response
 * 2. Error state on 500
 * 3. Query key includes status/sort/order
 *
 * Per batch-up-1-react-engr-prompt.md Test Requirements.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useWipReport, WIP_QUERY_KEY } from "../useWipReport";

// ─── MSW server ─────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/reports/wip", () => {
    return HttpResponse.json({
      report_type: "wip",
      generated_at: "2026-07-29T14:00:00Z",
      margin_target_pct: 20.0,
      row_count: 1,
      summary: {
        active_job_count: 1,
        total_actual_cost_cents: 42000,
        total_quoted_budget_cents: 60000,
        total_projected_cost_cents: 55000,
        jobs_over_budget_count: 0,
        jobs_below_margin_target_count: 0,
      },
      rows: [
        {
          job_id: "job-1",
          job_number: "JOB-000101",
          title: "Panel upgrade",
          customer_name: "Apex Commercial LLC",
          site_name: "North Warehouse",
          status_code: "in_progress",
          scheduled_start_at: "2026-07-20T13:00:00Z",
          quoted_budget_cents: 60000,
          actual_cost_cents: 42000,
          etc_hours_remaining: 6.5,
          etc_cost_cents: 13000,
          projected_cost_cents: 55000,
          projected_margin_pct: 8.33,
          budget_deviation_pct: 8.33,
          has_etc: true,
          below_margin_target: false,
        },
      ],
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Helpers ────────────────────────────────────────────────────────────────

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function wrapper(client: QueryClient) {
  function QueryWrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client }, children);
  }
  return QueryWrapper;
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("useWipReport", () => {
  it("returns the WIP report shape on success", async () => {
    const client = createQueryClient();
    const { result } = renderHook(() => useWipReport(), {
      wrapper: wrapper(client),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.report_type).toBe("wip");
    expect(result.current.data?.row_count).toBe(1);
    expect(result.current.data?.rows[0].job_number).toBe("JOB-000101");
    expect(result.current.data?.summary.active_job_count).toBe(1);
  });

  it("sets isError on 500 response", async () => {
    server.use(
      http.get("*/api/v1/reports/wip", () => {
        return HttpResponse.json(
          { detail: "Internal server error" },
          { status: 500 },
        );
      }),
    );

    const client = createQueryClient();
    const { result } = renderHook(() => useWipReport(), {
      wrapper: wrapper(client),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

// ─── Query Key ──────────────────────────────────────────────────────────────

describe("WIP_QUERY_KEY", () => {
  it("includes status, sort, and order with defaults", () => {
    const key = WIP_QUERY_KEY({});
    expect(key).toEqual([
      "wip-report",
      "scheduled,in_progress",
      "deviation_pct",
      "desc",
    ]);
  });

  it("includes custom status, sort, and order", () => {
    const key = WIP_QUERY_KEY({
      status: "in_progress",
      sort: "actual_cost_cents",
      order: "asc",
    });
    expect(key).toEqual([
      "wip-report",
      "in_progress",
      "actual_cost_cents",
      "asc",
    ]);
  });

  it("produces different keys for different sort values", () => {
    const key1 = WIP_QUERY_KEY({ sort: "deviation_pct" });
    const key2 = WIP_QUERY_KEY({ sort: "projected_margin_pct" });
    expect(key1).not.toEqual(key2);
  });
});
