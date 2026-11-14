/**
 * useOwnerArSummary unit tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/useOwnerArSummary.test.ts
 *
 * Verifies:
 *   - Invoice with due_at in the past → counted in overdueCount
 *   - Invoice with due_at in the future → not in overdueCount
 *   - outstandingCount matches total from response
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useOwnerArSummary } from "../../features/owner-tab/hooks/useOwnerArSummary";

// ── Mocks ──────────────────────────────────────────────────────────────────────

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "owner-001", role: "owner", tenantId: "tenant-001" },
    isAuthenticated: true,
    role: "owner",
  }),
}));

// ── Date helpers ───────────────────────────────────────────────────────────────

const PAST_DUE = new Date(Date.now() - 10 * 86_400_000).toISOString(); // 10 days ago
const FUTURE_DUE = new Date(Date.now() + 20 * 86_400_000).toISOString(); // 20 days from now

const BASE_INVOICE = {
  invoice_number: "INV-001",
  customer_id: "customer-001",
  site_id: "site-001",
  status_id: "status-sent",
  status_code: "sent",
  issued_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
  subtotal_cents: 100000,
  tax_cents: 8000,
  total_cents: 108000,
  balance_due_cents: 108000,
  currency: "USD",
  quote_id: null,
  job_id: null,
  created_at: new Date(Date.now() - 6 * 86_400_000).toISOString(),
  updated_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
};

// ── Server ─────────────────────────────────────────────────────────────────────

let capturedUrl: string | null = null;

const server = setupServer(
  http.get("*/api/v1/invoices/", ({ request }) => {
    capturedUrl = request.url;
    return HttpResponse.json({
      items: [
        { ...BASE_INVOICE, id: "invoice-001", due_at: PAST_DUE }, // overdue
        { ...BASE_INVOICE, id: "invoice-002", due_at: FUTURE_DUE }, // not overdue
        { ...BASE_INVOICE, id: "invoice-003", due_at: FUTURE_DUE }, // not overdue
      ],
      total: 3,
      limit: 50,
      offset: 0,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedUrl = null;
});
afterAll(() => server.close());

// ── Wrapper ────────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("useOwnerArSummary", () => {
  it("calls GET /api/v1/invoices/ with status=sent param", async () => {
    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(capturedUrl).not.toBeNull();
    const url = new URL(capturedUrl!);
    expect(url.searchParams.get("status")).toBe("sent");
  });

  it("outstandingCount matches total from response (not items.length)", async () => {
    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.outstandingCount).toBe(3);
  });

  it("invoice with due_at in the past is counted in overdueCount", async () => {
    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.overdueCount).toBe(1);
  });

  it("invoices with due_at in the future are NOT counted in overdueCount", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({
          items: [
            { ...BASE_INVOICE, id: "invoice-001", due_at: FUTURE_DUE },
            { ...BASE_INVOICE, id: "invoice-002", due_at: FUTURE_DUE },
          ],
          total: 2,
          limit: 50,
          offset: 0,
        }),
      ),
    );

    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.overdueCount).toBe(0);
    expect(result.current.data?.outstandingCount).toBe(2);
  });

  it("invoice with due_at=null is not counted as overdue", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({
          items: [
            { ...BASE_INVOICE, id: "invoice-001", due_at: null },
            { ...BASE_INVOICE, id: "invoice-002", due_at: null },
          ],
          total: 2,
          limit: 50,
          offset: 0,
        }),
      ),
    );

    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.overdueCount).toBe(0);
  });

  it("returns overdueCount=2 when all invoices are past due", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({
          items: [
            { ...BASE_INVOICE, id: "invoice-001", due_at: PAST_DUE },
            { ...BASE_INVOICE, id: "invoice-002", due_at: PAST_DUE },
          ],
          total: 2,
          limit: 50,
          offset: 0,
        }),
      ),
    );

    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.overdueCount).toBe(2);
    expect(result.current.data?.outstandingCount).toBe(2);
  });

  it("sets isError=true when API returns 500", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({ detail: "error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useOwnerArSummary(), { wrapper });

    // Wait for isError directly — hook has retry:1 which may delay isLoading→false
    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 5000,
    });

    expect(result.current.isError).toBe(true);
  });
});
