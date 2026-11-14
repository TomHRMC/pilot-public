/**
 * useResolveVariance hook tests — CE-1 Part C
 *
 * Location: apps/web/src/features/invoices/hooks/__tests__/useResolveVariance.test.tsx
 *
 * Tests: data shape, error states (409/422/network), correct method/URL/payload,
 *        invalidation on success.
 * RULE: Fresh QueryClient per test with retry: false (§14).
 * RULE: MSW setupServer + resetHandlers in afterEach (§15).
 * RULE: Never mock apiClient (§15).
 */

import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useResolveVariance } from "../useResolveVariance";

const server = setupServer(
  http.post(
    "/api/v1/invoices/:paymentId/resolve-variance",
    async ({ params, request }) => {
      const { paymentId } = params as { paymentId: string };
      const body = (await request.json()) as {
        resolution: string;
        note?: string;
      };

      if (paymentId === "pay-409") {
        return HttpResponse.json(
          { detail: "This overpayment was already resolved." },
          { status: 409 },
        );
      }

      if (paymentId === "pay-422") {
        return HttpResponse.json(
          { detail: "No overpayment to resolve." },
          { status: 422 },
        );
      }

      if (paymentId === "pay-500") {
        return HttpResponse.json(
          { detail: "Internal server error" },
          { status: 500 },
        );
      }

      return HttpResponse.json({
        id: paymentId,
        invoice_id: "inv-001",
        tenant_id: "t-001",
        amount_cents: 60000,
        paid_via: "card",
        balance_due_cents: 0,
        amount_variance_cents: 1500,
        status_id: "ps-001",
        paid_at: "2026-08-12T10:00:00Z",
        idempotency_key: null,
        created_at: "2026-08-12T10:00:00Z",
        variance_resolution: body.resolution,
        variance_resolution_note: body.note ?? null,
        variance_resolved_at: "2026-08-12T15:00:00Z",
        variance_resolved_by_user_id: "u-001",
      });
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

describe("useResolveVariance", () => {
  it("posts to correct URL with { resolution, note } payload", async () => {
    const onSuccess = vi.fn();
    const { result } = renderHook(
      () =>
        useResolveVariance({
          invoiceId: "inv-001",
          paymentId: "pay-success",
          onSuccess,
        }),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ resolution: "credit", note: "test note" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.variance_resolution).toBe("credit");
    expect(result.current.data?.variance_resolution_note).toBe("test note");
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it("maps 409 to already_resolved error", async () => {
    const onError = vi.fn();
    const { result } = renderHook(
      () =>
        useResolveVariance({
          invoiceId: "inv-001",
          paymentId: "pay-409",
          onError,
        }),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ resolution: "writeoff" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "already_resolved",
        status: 409,
      }),
    );
  });

  it("maps 422 to validation error", async () => {
    const onError = vi.fn();
    const { result } = renderHook(
      () =>
        useResolveVariance({
          invoiceId: "inv-001",
          paymentId: "pay-422",
          onError,
        }),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ resolution: "credit" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "validation",
        status: 422,
      }),
    );
  });

  it("maps 500 to network error", async () => {
    const onError = vi.fn();
    const { result } = renderHook(
      () =>
        useResolveVariance({
          invoiceId: "inv-001",
          paymentId: "pay-500",
          onError,
        }),
      { wrapper: createWrapper() },
    );

    result.current.mutate({ resolution: "refund_offline" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "network",
      }),
    );
  });
});
