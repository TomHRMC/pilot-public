/**
 * PLP-FIX-10 Integration — Generate-&-Copy-Link gate (INV-BUG-16)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_10/generate-link-gate.integration.test.tsx
 *
 * Tests:
 * - accountant (lacks invoices.update) → no Generate-&-Copy-Link button
 * - owner (invoices.update) → button present
 * - office_staff (lacks invoices.update) → no button
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InvoiceDetailPage } from "@/features/invoices/components/InvoiceDetailPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/invoices",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

// ── MSW server ───────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuth(role: PilotRole): AuthContextValue {
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  return {
    user: {
      id: "u1",
      email: `${role}@pilot-dev.example.com`,
      role,
      tenantId: "t1",
      displayName: role,
      accessToken: "tok",
      permissions: perms,
    },
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
    whenSessionReady: vi.fn(),
  };
}

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithAuth(ui: React.ReactElement, role: PilotRole) {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>{ui}</NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── MSW invoice data ─────────────────────────────────────────────────────────

const INVOICE_ID = "inv-test-gate-001";

function setupInvoiceHandlers() {
  server.use(
    http.get("*/api/v1/invoices/:invoiceId", ({ params }) => {
      const { invoiceId } = params as { invoiceId: string };
      if (invoiceId !== INVOICE_ID) {
        return HttpResponse.json({ detail: "Not found" }, { status: 404 });
      }
      return HttpResponse.json({
        id: INVOICE_ID,
        tenant_id: "t1",
        invoice_number: "INV-TEST-001",
        customer_id: "c-00000001-0000-0000-0000-000000000001",
        site_id: null,
        status_id: "st-issued",
        status_code: "issued",
        quote_id: null,
        job_id: null,
        idempotency_key: "idem-test",
        issued_at: "2026-09-06T00:00:00Z",
        due_at: "2026-09-20T00:00:00Z",
        subtotal_cents: 50000,
        tax_cents: 4000,
        total_cents: 54000,
        balance_due_cents: 54000,
        currency: "USD",
        customer_notes: null,
        terms_and_conditions: null,
        pdf_object_key: null,
        is_active: true,
        created_at: "2026-09-06T10:00:00Z",
        updated_at: "2026-09-06T10:00:00Z",
        created_by: null,
        updated_by: null,
        lines: [],
        payments: [],
      });
    }),
    http.get("*/api/v1/customers/:customerId", () =>
      HttpResponse.json({
        id: "c-00000001-0000-0000-0000-000000000001",
        display_name: "Test Customer",
        customer_type: "person",
        is_active: true,
      }),
    ),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-10 — Generate-&-Copy-Link gate (INV-BUG-16)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("accountant (lacks invoices.update) → no Generate-&-Copy-Link button", async () => {
    setupInvoiceHandlers();
    renderWithAuth(<InvoiceDetailPage invoiceId={INVOICE_ID} />, "accountant");

    // Wait for invoice to load
    await waitFor(() => {
      expect(screen.getByTestId("invoice-detail-page")).toBeInTheDocument();
    });

    // The Generate & Copy Link button should NOT be present
    expect(
      screen.queryByTestId("copy-public-link-btn"),
    ).not.toBeInTheDocument();
  });

  it("office_staff (lacks invoices.update) → no Generate-&-Copy-Link button", async () => {
    setupInvoiceHandlers();
    renderWithAuth(
      <InvoiceDetailPage invoiceId={INVOICE_ID} />,
      "office_staff",
    );

    await waitFor(() => {
      expect(screen.getByTestId("invoice-detail-page")).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("copy-public-link-btn"),
    ).not.toBeInTheDocument();
  });

  it("owner (invoices.update) → Generate-&-Copy-Link button present", async () => {
    setupInvoiceHandlers();
    renderWithAuth(<InvoiceDetailPage invoiceId={INVOICE_ID} />, "owner");

    await waitFor(() => {
      expect(screen.getByTestId("invoice-detail-page")).toBeInTheDocument();
    });

    expect(screen.getByTestId("copy-public-link-btn")).toBeInTheDocument();
  });
});
