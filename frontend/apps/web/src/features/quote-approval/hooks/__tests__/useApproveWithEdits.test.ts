/**
 * useApproveWithEdits unit tests
 *
 * Location: apps/web/src/features/quote-approval/hooks/__tests__/useApproveWithEdits.test.ts
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useApproveWithEdits } from "@pilot/ui/hooks";

const server = setupServer(
  http.get("/api/v1/quotes/:id/pending-edits", () => HttpResponse.json([])),
  http.post("/api/v1/quotes/:id/pending-edits", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: "edit-1",
      quote_id: "quote-1",
      affected_line_item_id: "line-1",
      edit_type: "field_edit",
      field_name: body["field_name"] ?? "unit_price_cents",
      old_value: "150000",
      new_value: "175000",
      created_at: new Date().toISOString(),
    });
  }),
  http.delete(
    "/api/v1/quotes/:id/pending-edits",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.post("/api/v1/quotes/:id/approve", () =>
    HttpResponse.json({
      id: "quote-1",
      status: "approved",
      quote_version_id: "qv-2",
      approved_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe("useApproveWithEdits", () => {
  it("hasPendingEdits is false initially", async () => {
    const { result } = renderHook(
      () => useApproveWithEdits({ quoteId: "quote-1", quoteVersionId: "qv-1" }),
      { wrapper },
    );
    await waitFor(() => {
      expect(result.current.hasPendingEdits).toBe(false);
    });
  });

  it("hasPendingEdits becomes true after stagePendingEdit", async () => {
    // Override pending-edits GET to return one edit after staging
    let staged = false;
    server.use(
      http.get("/api/v1/quotes/:id/pending-edits", () => {
        if (staged) {
          return HttpResponse.json([
            {
              id: "edit-1",
              quote_id: "quote-1",
              affected_line_item_id: "line-1",
              edit_type: "field_edit",
              field_name: "unit_price_cents",
              old_value: "150000",
              new_value: "175000",
              created_at: new Date().toISOString(),
            },
          ]);
        }
        return HttpResponse.json([]);
      }),
    );

    const { result } = renderHook(
      () => useApproveWithEdits({ quoteId: "quote-1", quoteVersionId: "qv-1" }),
      { wrapper },
    );

    await act(async () => {
      staged = true;
      await result.current.stagePendingEdit({
        edit_type: "field_edit",
        affected_line_item_id: "line-1",
        field_name: "unit_price_cents",
        old_value: "150000",
        new_value: "175000",
      });
    });

    await waitFor(() => expect(result.current.hasPendingEdits).toBe(true));
  });

  it("approveWithEdits calls mutate with apply_pending_edits: true", async () => {
    let approveBody: unknown = null;
    server.use(
      http.post("/api/v1/quotes/:id/approve", async ({ request }) => {
        approveBody = await request.json();
        return HttpResponse.json({
          id: "quote-1",
          status: "approved",
          quote_version_id: "qv-2",
          approved_at: new Date().toISOString(),
        });
      }),
    );

    const { result } = renderHook(
      () => useApproveWithEdits({ quoteId: "quote-1", quoteVersionId: "qv-1" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isApproving).toBe(false));

    act(() => {
      result.current.approveWithEdits();
    });

    await waitFor(() => {
      expect(approveBody).toMatchObject({ apply_pending_edits: true });
    });
  });

  it("approveAsIs calls mutate with apply_pending_edits: false", async () => {
    let approveBody: unknown = null;
    server.use(
      http.post("/api/v1/quotes/:id/approve", async ({ request }) => {
        approveBody = await request.json();
        return HttpResponse.json({
          id: "quote-1",
          status: "approved",
          quote_version_id: "qv-2",
          approved_at: new Date().toISOString(),
        });
      }),
    );

    const { result } = renderHook(
      () => useApproveWithEdits({ quoteId: "quote-1", quoteVersionId: "qv-1" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isApproving).toBe(false));

    act(() => {
      result.current.approveAsIs();
    });

    await waitFor(() => {
      expect(approveBody).toMatchObject({ apply_pending_edits: false });
    });
  });
});
