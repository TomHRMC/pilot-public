/**
 * useSignoffContext unit tests
 *
 * Location: apps/mobile/features/jobs/hooks/__tests__/useSignoffContext.test.tsx
 *
 * Tests:
 *   - Data shape from mocked apiClient
 *   - Error state
 *   - Query-key construction
 *
 * TEST-UPLIFT-1C: Converted from jest.mock("@pilot/shared-api") to MSW
 * setupServer + wildcard handlers (Rule 18). The banned apiClient mock was
 * removed; MSW interception at the HTTP level proves apiClient.get() is the
 * transport. The shared server is now usable (voice WS handler isolated).
 */

import React from "react";
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  useSignoffContext,
  SIGNOFF_CONTEXT_QUERY_KEY,
} from "../useSignoffContext";

// ── Helpers ───────────────────────────────────────────────────────────────────

const JOB_ID = "job-signoff-test-001";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

const FIXTURE = {
  job_id: JOB_ID,
  customer_display_name: "John Smith",
  invoices: [
    {
      invoice_id: "invoice-signoff-001",
      invoice_number: "INV-0042",
      status: "issued",
      total_cents: 125000,
      balance_due_cents: 125000,
      currency: "USD",
      terms_text: "Standard terms apply.",
      active_signoff: null,
    },
  ],
};

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId/signoff-context", ({ params }) => {
    // Return the fixture keyed to the requested job ID
    return HttpResponse.json({ ...FIXTURE, job_id: String(params.jobId) });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useSignoffContext", () => {
  it("fetches signoff context data", async () => {
    const { result } = renderHook(() => useSignoffContext(JOB_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isPending).toBe(false));

    expect(result.current.data).toBeTruthy();
    expect(result.current.data?.job_id).toBe(JOB_ID);
    expect(result.current.data?.invoices.length).toBeGreaterThan(0);
    expect(result.current.data?.invoices[0]?.invoice_number).toBe("INV-0042");
  });

  it("handles error state", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId/signoff-context", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Network Error",
            status: 500,
            detail: "Network error",
          },
          { status: 500 },
        ),
      ),
    );

    const { result } = renderHook(() => useSignoffContext(JOB_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });

  it("uses correct query key", () => {
    expect(SIGNOFF_CONTEXT_QUERY_KEY).toBe("job-signoff-context");
  });
});
