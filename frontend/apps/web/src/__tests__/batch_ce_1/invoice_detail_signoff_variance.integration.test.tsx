/**
 * CE-1 Part C Integration — Invoice Detail: Sign-off Card + Overpayment Review
 *
 * Location: apps/web/src/__tests__/batch_ce_1/invoice_detail_signoff_variance.integration.test.tsx
 *
 * Tests:
 * 1. Page renders (no 404) with signoff card + overpayment banner
 * 2. RBAC: owner sees banner + card; tech sees neither
 * 3. Banner → modal → resolve happy path fires POST to exact URL with { resolution, note }
 * 4. Banner collapses on refetch after resolve
 *
 * RULE: Fresh QueryClient per test with retry: false (§14).
 * RULE: MSW setupServer + resetHandlers in afterEach (§15).
 * RULE: AuthContext.Provider for RBAC (§15).
 * RULE: Never mock apiClient (§15).
 * RULE: Assert by specific content/ID, never counts (§15).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InvoiceDetailPage } from "@/features/invoices/components/InvoiceDetailPage";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices/inv-ce1-test",
  useSearchParams: () => new URLSearchParams(),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const INVOICE_ID = "inv-ce1-test-0000-0000-0000-000000000001";
const PAYMENT_ID = "pay-ce1-over-0000-0000-0000-000000000001";

const MOCK_INVOICE_WITH_OVERPAYMENT = {
  id: INVOICE_ID,
  tenant_id: "t-001",
  invoice_number: "INV-CE1-TEST",
  customer_id: "c-00000001-0000-0000-0000-000000000001",
  site_id: null,
  status_id: "st-issued-001",
  status_code: "issued",
  quote_id: null,
  job_id: null,
  idempotency_key: null,
  issued_at: "2026-08-12T00:00:00Z",
  due_at: "2026-08-30T00:00:00Z",
  subtotal_cents: 50000,
  tax_cents: 0,
  total_cents: 50000,
  balance_due_cents: 0,
  currency: "USD",
  customer_notes: null,
  terms_and_conditions: null,
  pdf_object_key: null,
  is_active: true,
  created_at: "2026-08-12T10:00:00Z",
  updated_at: "2026-08-12T10:00:00Z",
  created_by: null,
  updated_by: null,
  lines: [],
  payments: [
    {
      id: PAYMENT_ID,
      amount_cents: 51500,
      paid_at: "2026-08-12T10:00:00Z",
      paid_via: "card",
      psp_provider: "stripe",
      customer_payment_comment: "Customer overpaid",
      status_id: "ps-001",
      amount_variance_cents: 1500,
      variance_resolution: null,
      variance_resolution_note: null,
      variance_resolved_at: null,
      variance_resolved_by_user_id: null,
    },
  ],
};

const MOCK_SIGNOFF = {
  signoff: {
    signoff_id: "so-ce1-001",
    invoice_id: INVOICE_ID,
    signed_by_name: "John Smith",
    signed_at: "2026-08-12T14:30:00Z",
    client_capture_at: null,
    captured_by_user_id: "u-tech-001",
    signature_url: "https://example.com/sig.png",
  },
  superseded_count: 0,
};

// Track resolve calls
let resolveCallBody: { resolution: string; note?: string } | null = null;
let resolveCallUrl: string | null = null;

const server = setupServer(
  // Invoice detail
  http.get("/api/v1/invoices/:invoiceId", () => {
    return HttpResponse.json(MOCK_INVOICE_WITH_OVERPAYMENT);
  }),

  // Signoff
  http.get("/api/v1/invoices/:invoiceId/signoff", () => {
    return HttpResponse.json(MOCK_SIGNOFF);
  }),

  // Resolve variance — tracks the call
  http.post(
    "/api/v1/invoices/:paymentId/resolve-variance",
    async ({ params, request }) => {
      const { paymentId } = params as { paymentId: string };
      resolveCallUrl = `/api/v1/invoices/${paymentId}/resolve-variance`;
      resolveCallBody = (await request.json()) as {
        resolution: string;
        note?: string;
      };

      return HttpResponse.json({
        id: paymentId,
        invoice_id: INVOICE_ID,
        tenant_id: "t-001",
        amount_cents: 51500,
        paid_via: "card",
        balance_due_cents: 0,
        amount_variance_cents: 1500,
        status_id: "ps-001",
        paid_at: "2026-08-12T10:00:00Z",
        idempotency_key: null,
        created_at: "2026-08-12T10:00:00Z",
        variance_resolution: resolveCallBody.resolution,
        variance_resolution_note: resolveCallBody.note ?? null,
        variance_resolved_at: new Date().toISOString(),
        variance_resolved_by_user_id: "u-001",
      });
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  resolveCallBody = null;
  resolveCallUrl = null;
});
afterAll(() => server.close());

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeAuthContext(role: PilotRole): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "test@example.com",
      role,
      tenantId: "t-001",
      displayName: "Test User",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper(role: PilotRole = "owner") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const ctx = makeAuthContext(role);
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

describe("CE-1 Part C — Invoice Detail Sign-off + Variance Integration", () => {
  it("1. page renders with overpayment banner and signoff card (owner)", async () => {
    render(<InvoiceDetailPage invoiceId={INVOICE_ID} />, {
      wrapper: createWrapper("owner"),
    });

    // Banner appears
    await waitFor(() => {
      expect(
        screen.getByTestId("overpayment-review-banner"),
      ).toBeInTheDocument();
    });

    // Headline copy
    expect(screen.getByTestId("overpayment-headline")).toHaveTextContent(
      "Customer paid $15.00 over invoice total — review.",
    );

    // Signoff card appears (after data loads)
    await waitFor(() => {
      expect(screen.getByTestId("signoff-card")).toBeInTheDocument();
    });

    // Signer name visible
    expect(screen.getByText("John Smith")).toBeInTheDocument();
  });

  it("2. RBAC: tech sees neither banner nor card (invoices.view absent)", async () => {
    render(<InvoiceDetailPage invoiceId={INVOICE_ID} />, {
      wrapper: createWrapper("technician"),
    });

    // Wait for invoice to load
    await waitFor(() => {
      expect(screen.getByTestId("invoice-detail-page")).toBeInTheDocument();
    });

    // Banner hidden (RoleGate invoices.view)
    expect(
      screen.queryByTestId("overpayment-review-banner"),
    ).not.toBeInTheDocument();

    // Card hidden (RoleGate invoices.view)
    expect(screen.queryByTestId("signoff-card")).not.toBeInTheDocument();
  });

  it("3. banner → modal → resolve fires POST with { resolution, note } payload", async () => {
    render(<InvoiceDetailPage invoiceId={INVOICE_ID} />, {
      wrapper: createWrapper("owner"),
    });

    // Wait for banner
    await waitFor(() => {
      expect(screen.getByTestId("resolve-variance-btn")).toBeInTheDocument();
    });

    // Click Resolve
    fireEvent.click(screen.getByTestId("resolve-variance-btn"));

    // Modal opens
    await waitFor(() => {
      expect(screen.getByTestId("resolve-variance-modal")).toBeInTheDocument();
    });

    // Select credit
    fireEvent.click(
      screen.getByTestId("resolution-option-credit").querySelector("input")!,
    );

    // Type a note
    fireEvent.change(screen.getByTestId("resolve-variance-note"), {
      target: { value: "Applied as credit forward" },
    });

    // Submit
    fireEvent.click(screen.getByTestId("resolve-variance-submit"));

    // Verify POST was called with correct URL and payload
    await waitFor(() => {
      expect(resolveCallUrl).toBe(
        `/api/v1/invoices/${PAYMENT_ID}/resolve-variance`,
      );
    });

    expect(resolveCallBody).toEqual({
      resolution: "credit",
      note: "Applied as credit forward",
    });
  });

  it("4. banner collapses to resolved line after successful resolve", async () => {
    // Override the invoice handler to return resolved payment after first fetch
    let resolveCount = 0;
    server.use(
      http.get("/api/v1/invoices/:invoiceId", () => {
        if (resolveCount > 0) {
          // Return invoice with resolved payment
          return HttpResponse.json({
            ...MOCK_INVOICE_WITH_OVERPAYMENT,
            payments: [
              {
                ...MOCK_INVOICE_WITH_OVERPAYMENT.payments[0],
                variance_resolution: "credit",
                variance_resolution_note: "Applied as credit",
                variance_resolved_at: "2026-08-13T10:00:00Z",
                variance_resolved_by_user_id: "u-001",
              },
            ],
          });
        }
        resolveCount++;
        return HttpResponse.json(MOCK_INVOICE_WITH_OVERPAYMENT);
      }),
    );

    render(<InvoiceDetailPage invoiceId={INVOICE_ID} />, {
      wrapper: createWrapper("owner"),
    });

    // Wait for banner
    await waitFor(() => {
      expect(screen.getByTestId("resolve-variance-btn")).toBeInTheDocument();
    });

    // Click Resolve
    fireEvent.click(screen.getByTestId("resolve-variance-btn"));

    // Select and submit
    await waitFor(() => {
      expect(screen.getByTestId("resolve-variance-modal")).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByTestId("resolution-option-writeoff").querySelector("input")!,
    );
    fireEvent.click(screen.getByTestId("resolve-variance-submit"));

    // Banner should collapse to resolved line after refetch
    await waitFor(() => {
      expect(
        screen.getByTestId("overpayment-resolved-line"),
      ).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("overpayment-review-banner"),
    ).not.toBeInTheDocument();
  });
});
