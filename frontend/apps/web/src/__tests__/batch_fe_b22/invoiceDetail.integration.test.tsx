/**
 * FE-B22 Integration — Invoice Detail
 *
 * Location: apps/web/src/__tests__/batch_fe_b22/invoiceDetail.integration.test.tsx
 *
 * Tests:
 * 1. /invoices/[id] renders invoice detail with line items (no longer 404)
 * 2. "Send Invoice" button opens SendInvoicePreviewModal
 * 3. "Cancel" in modal does NOT fire useSendInvoice
 * 4. "Record Payment" button opens RecordPaymentModal
 * 5. "Record Payment" button hidden when balance_due_cents = 0
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
  beforeEach,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InvoiceDetailPage } from "@/features/invoices/components/InvoiceDetailPage";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices/inv-00000001-0000-0000-0000-000000000001",
  useSearchParams: () => new URLSearchParams(),
}));

// ── MSW server ─────────────────────────────────────────────────────────────────

const MOCK_INVOICE_LINES = [
  {
    id: "il-0001",
    invoice_id: "inv-00000001-0000-0000-0000-000000000001",
    source_type: "catalog_item",
    source_id: "ci-0001",
    description: "200A Service Panel Upgrade",
    quantity: 1,
    unit_price_cents: 45000,
    subtotal_cents: 45000,
    tax_amount_cents: 3713,
    total_cents: 48713,
    sort_order: 0,
  },
];

const MOCK_INVOICE = {
  id: "inv-00000001-0000-0000-0000-000000000001",
  tenant_id: "t-001",
  invoice_number: "INV-20260616-0001",
  customer_id: "c-00000001-0000-0000-0000-000000000001",
  site_id: null,
  status_id: "st-draft-0001",
  status_code: "draft",
  quote_id: null,
  job_id: null,
  idempotency_key: null,
  issued_at: "2026-06-16T00:00:00Z",
  due_at: "2026-06-30T00:00:00Z",
  subtotal_cents: 45000,
  tax_cents: 3713,
  total_cents: 48713,
  balance_due_cents: 48713,
  currency: "USD",
  customer_notes: null,
  terms_and_conditions: null,
  pdf_object_key: null,
  is_active: true,
  created_at: "2026-06-16T10:00:00Z",
  updated_at: "2026-06-16T10:00:00Z",
  created_by: null,
  updated_by: null,
  lines: MOCK_INVOICE_LINES,
};

const MOCK_INVOICE_PAID = {
  ...MOCK_INVOICE,
  id: "inv-paid-0000-0000-0000-000000000002",
  invoice_number: "INV-20260610-0002",
  status_code: "paid",
  balance_due_cents: 0,
};

const server = setupServer(
  http.get("/api/v1/invoices/:invoiceId", ({ params }) => {
    const { invoiceId } = params as { invoiceId: string };
    if (invoiceId === "inv-paid-0000-0000-0000-000000000002") {
      return HttpResponse.json(MOCK_INVOICE_PAID);
    }
    return HttpResponse.json(MOCK_INVOICE);
  }),
  http.post("/api/v1/invoices/:invoiceId/send", () => {
    return HttpResponse.json(
      {
        id: "pl-0001",
        tenant_id: "t-001",
        invoice_id: "inv-00000001-0000-0000-0000-000000000001",
        contact_id: "c-0001",
        signed_token: "mock-token-abc",
        expires_at: "2026-07-16T00:00:00Z",
        max_uses: 10,
        used_count: 0,
        status: "active",
        last_used_at: null,
        created_at: "2026-06-16T10:00:00Z",
      },
      { status: 201 },
    );
  }),
  http.post(
    "/api/v1/invoices/:invoiceId/record-payment",
    async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(
        {
          id: "pay-0001",
          invoice_id: "inv-00000001-0000-0000-0000-000000000001",
          tenant_id: "t-001",
          amount_cents: body.amount_cents,
          paid_via: body.paid_via,
          balance_due_cents: 0,
          amount_variance_cents: 0,
          status_id: "fa70374c-513a-4cc3-baca-22a54a594a4d",
          paid_at: new Date().toISOString(),
          idempotency_key: null,
          created_at: new Date().toISOString(),
        },
        { status: 201 },
      );
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeAuthContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@example.com",
      role: "owner",
      tenantId: "t-001",
      displayName: "Test Owner",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const ctx = makeAuthContext();
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={ctx}>
        <QueryClientProvider client={qc}>
          <NotificationQueueProvider>{children}</NotificationQueueProvider>
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  return Wrapper;
}

// ── Tests ───────────────────────────────────────────────────────────────────────

describe("FE-B22 Invoice Detail Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders invoice detail with line items — route no longer 404", async () => {
    render(
      <InvoiceDetailPage invoiceId="inv-00000001-0000-0000-0000-000000000001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId("invoice-detail-page")).toBeTruthy();
    });

    // Invoice number appears multiple times (header + breadcrumb) — check testid renders
    const invoiceNums = screen.getAllByText("INV-20260616-0001");
    expect(invoiceNums.length).toBeGreaterThan(0);
    expect(screen.getByText("200A Service Panel Upgrade")).toBeTruthy();
  });

  it("2. Send Invoice button opens SendInvoicePreviewModal for draft invoice", async () => {
    render(
      <InvoiceDetailPage invoiceId="inv-00000001-0000-0000-0000-000000000001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId("send-invoice-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("send-invoice-btn"));

    await waitFor(() => {
      expect(screen.getByText("Send Invoice to Customer")).toBeTruthy();
    });
  });

  it("3. Cancel in SendInvoicePreviewModal does NOT fire useSendInvoice", async () => {
    render(
      <InvoiceDetailPage invoiceId="inv-00000001-0000-0000-0000-000000000001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId("send-invoice-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("send-invoice-btn"));

    await waitFor(() => {
      expect(screen.getByText("Cancel")).toBeTruthy();
    });

    // Track network calls — Cancel should close modal without sending
    let sendCalled = false;
    server.use(
      http.post("/api/v1/invoices/:invoiceId/send", () => {
        sendCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    fireEvent.click(screen.getByText("Cancel"));

    // Modal should close
    await waitFor(() => {
      expect(screen.queryByText("Send Invoice to Customer")).toBeNull();
    });

    expect(sendCalled).toBe(false);
  });

  it("4. Record Payment button opens RecordPaymentModal for unpaid invoice", async () => {
    render(
      <InvoiceDetailPage invoiceId="inv-00000001-0000-0000-0000-000000000001" />,
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(screen.getByTestId("record-payment-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("record-payment-btn"));

    await waitFor(() => {
      // When modal is open the Amount input field is present
      expect(screen.getByLabelText(/amount/i)).toBeTruthy();
    });
  });

  it("5. Record Payment button hidden when balance_due_cents = 0", async () => {
    render(
      <InvoiceDetailPage invoiceId="inv-paid-0000-0000-0000-000000000002" />,
      { wrapper: createWrapper() },
    );

    // Paid invoice has distinct invoice number INV-20260610-0002
    await waitFor(() => {
      expect(screen.getByTestId("invoice-detail-page")).toBeTruthy();
    });

    expect(screen.queryByTestId("record-payment-btn")).toBeNull();
  });
});
