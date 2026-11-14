/**
 * useInvoiceSignoff hook tests — CE-1 Part C
 *
 * Location: apps/web/src/features/invoices/hooks/__tests__/useInvoiceSignoff.test.tsx
 *
 * Tests: data shape, error states, query-key construction, correct method/URL.
 * RULE: Fresh QueryClient per test with retry: false (§14).
 * RULE: MSW setupServer + resetHandlers in afterEach (§15).
 * RULE: Never mock apiClient (§15).
 */

import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useInvoiceSignoff, SIGNOFF_QUERY_KEY } from "../useInvoiceSignoff";

const server = setupServer(
  http.get("/api/v1/invoices/:invoiceId/signoff", ({ params }) => {
    const { invoiceId } = params as { invoiceId: string };
    if (invoiceId === "inv-null-signoff") {
      return HttpResponse.json({ signoff: null, superseded_count: 0 });
    }
    if (invoiceId === "inv-error-signoff") {
      return HttpResponse.json(
        { detail: "Internal server error" },
        { status: 500 },
      );
    }
    return HttpResponse.json({
      signoff: {
        signoff_id: "so-001",
        invoice_id: invoiceId,
        signed_by_name: "John Smith",
        signed_at: "2026-08-12T14:30:00Z",
        client_capture_at: null,
        captured_by_user_id: "u-tech-001",
        signature_url: "https://example.com/sig.png",
      },
      superseded_count: 2,
    });
  }),
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

describe("useInvoiceSignoff", () => {
  it("query key is ['invoice', invoiceId, 'signoff']", () => {
    const key = SIGNOFF_QUERY_KEY("inv-123");
    expect(key).toEqual(["invoice", "inv-123", "signoff"]);
  });

  it("fetches populated signoff with correct data shape", async () => {
    const { result } = renderHook(
      () => useInvoiceSignoff("inv-00000001-0000-0000-0000-000000000001"),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.signoff).not.toBeNull();
    expect(result.current.data?.signoff?.signed_by_name).toBe("John Smith");
    expect(result.current.data?.signoff?.signature_url).toBe(
      "https://example.com/sig.png",
    );
    expect(result.current.data?.supersededCount).toBe(2);
  });

  it("returns null signoff when API returns { signoff: null }", async () => {
    const { result } = renderHook(() => useInvoiceSignoff("inv-null-signoff"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.signoff).toBeNull();
    expect(result.current.data?.supersededCount).toBe(0);
  });

  it("sets isError on 500 response", async () => {
    const { result } = renderHook(
      () => useInvoiceSignoff("inv-error-signoff"),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });

  it("is not enabled when invoiceId is null", () => {
    const { result } = renderHook(() => useInvoiceSignoff(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});
