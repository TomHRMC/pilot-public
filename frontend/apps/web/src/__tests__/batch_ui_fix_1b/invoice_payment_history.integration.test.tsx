/**
 * Invoice Payment History integration tests — UI-FIX-1B / FIX-013-FE
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_1b/invoice_payment_history.integration.test.tsx
 *
 * Tests that InvoicePaymentHistory correctly renders when payments are passed
 * from InvoiceDetailPage via the updated useInvoice hook.
 *
 * Platform: Web (Vitest + @testing-library/react + MSW)
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { InvoicePaymentHistory } from "../../features/invoices/components/InvoicePaymentHistory";

// ── Next.js mocks ─────────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  usePathname: () => "/invoices/inv-00000001-0000-0000-0000-000000000001",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

// ── MSW server setup ──────────────────────────────────────────────────────────
const server = setupServer(
  http.get("/api/v1/invoices/inv-with-payments", () => {
    return HttpResponse.json({
      id: "inv-with-payments",
      tenant_id: "t-00000001",
      invoice_number: "INV-TEST-001",
      customer_id: "c-00000001",
      site_id: null,
      status_id: "st-issued-001",
      status_code: "issued",
      quote_id: null,
      job_id: null,
      idempotency_key: null,
      issued_at: "2026-07-01T00:00:00Z",
      due_at: "2026-07-31T00:00:00Z",
      subtotal_cents: 100000,
      tax_cents: 8250,
      total_cents: 108250,
      balance_due_cents: 28250,
      currency: "USD",
      customer_notes: null,
      terms_and_conditions: null,
      pdf_object_key: null,
      is_active: true,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
      created_by: null,
      updated_by: null,
      lines: [],
      payments: [
        {
          id: "pay-test-001",
          amount_cents: 80000,
          paid_at: "2026-07-10T00:00:00Z",
          paid_via: "check",
          psp_provider: null,
          customer_payment_comment: "Partial payment — check #1042",
          status_id: "ps-001",
        },
      ],
    });
  }),
  http.get("/api/v1/invoices/inv-no-payments", () => {
    return HttpResponse.json({
      id: "inv-no-payments",
      tenant_id: "t-00000001",
      invoice_number: "INV-TEST-002",
      customer_id: "c-00000001",
      site_id: null,
      status_id: "st-issued-002",
      status_code: "issued",
      quote_id: null,
      job_id: null,
      idempotency_key: null,
      issued_at: "2026-07-01T00:00:00Z",
      due_at: "2026-07-31T00:00:00Z",
      subtotal_cents: 50000,
      tax_cents: 4125,
      total_cents: 54125,
      balance_due_cents: 54125,
      currency: "USD",
      customer_notes: null,
      terms_and_conditions: null,
      pdf_object_key: null,
      is_active: true,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
      created_by: null,
      updated_by: null,
      lines: [],
      payments: [],
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test wrapper ──────────────────────────────────────────────────────────────
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InvoicePaymentHistory — UI-FIX-1B / FIX-013-FE", () => {
  it("renders payment rows when payments array is populated", async () => {
    const payments = [
      {
        id: "pay-test-001",
        amount_cents: 80000,
        paid_at: "2026-07-10T00:00:00Z",
        paid_via: "check",
        psp_provider: null,
        customer_payment_comment: "Partial payment — check #1042",
      },
    ];

    render(<InvoicePaymentHistory payments={payments} />, {
      wrapper: createWrapper(),
    });

    // Payment table should be visible
    expect(screen.getByTestId("payment-history-table")).toBeInTheDocument();

    // Amount should be formatted as currency
    expect(screen.getByText("$800.00")).toBeInTheDocument();

    // Method should display
    expect(screen.getByText("check")).toBeInTheDocument();

    // Reference shows customer_payment_comment
    expect(
      screen.getByText("Partial payment — check #1042"),
    ).toBeInTheDocument();
  });

  it("shows empty state when payments array is empty", async () => {
    render(<InvoicePaymentHistory payments={[]} />, {
      wrapper: createWrapper(),
    });

    // Empty state text should be visible
    expect(screen.getByText(/no payments recorded/i)).toBeInTheDocument();

    // Payment table should NOT be present
    expect(screen.queryByTestId("payment-history-table")).toBeNull();
  });

  it("shows empty state when payments prop is omitted (defaults to empty)", () => {
    render(<InvoicePaymentHistory />, { wrapper: createWrapper() });

    expect(screen.getByText(/no payments recorded/i)).toBeInTheDocument();
  });

  it("renders psp_provider as Reference fallback when comment is null", () => {
    const payments = [
      {
        id: "pay-test-002",
        amount_cents: 50000,
        paid_at: "2026-07-15T00:00:00Z",
        paid_via: "card",
        psp_provider: "stripe",
        customer_payment_comment: null,
      },
    ];

    render(<InvoicePaymentHistory payments={payments} />, {
      wrapper: createWrapper(),
    });

    // psp_provider shown as fallback
    expect(screen.getByText("stripe")).toBeInTheDocument();
  });

  it("renders '—' for Reference when both comment and psp_provider are null", () => {
    const payments = [
      {
        id: "pay-test-003",
        amount_cents: 25000,
        paid_at: "2026-07-20T00:00:00Z",
        paid_via: "cash",
        psp_provider: null,
        customer_payment_comment: null,
      },
    ];

    render(<InvoicePaymentHistory payments={payments} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
