/**
 * FE-B29 Integration — Invoice Builder Save
 *
 * Location: apps/web/src/__tests__/batch_fe_b29/invoice_builder_save.integration.test.tsx
 *
 * Tests:
 * 1. Validation blocks save when customer not selected
 * 2. Default billing_mode is line_item — toggle button visible
 * 3. On POST 412, TaxSetupSubFlowModal modal pre-condition check
 * 4. Preview Invoice button is disabled (deferred per design doc §G)
 */

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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser } from "@pilot/ui/auth";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Navigation mock ───────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  usePathname: () => "/invoices/new",
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
beforeEach(() => {
  mockPush.mockClear();
  mockBack.mockClear();
});

// ── MSW ───────────────────────────────────────────────────────────────────────

const MOCK_NEW_INVOICE = {
  id: "inv-new-0000-0000-0000-000000000099",
  tenant_id: "t-00000001",
  invoice_number: "INV-20260712-0099",
  customer_id: "c-00000001",
  site_id: "s-00000001",
  status_id: "st-draft-0000",
  status_code: "draft",
  quote_id: null,
  job_id: null,
  idempotency_key: null,
  issued_at: new Date().toISOString(),
  due_at: null,
  subtotal_cents: 0,
  tax_cents: 0,
  total_cents: 0,
  balance_due_cents: 0,
  currency: "USD",
  customer_notes: null,
  terms_and_conditions: null,
  pdf_object_key: null,
  is_active: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  created_by: null,
  updated_by: null,
  lines: [],
};

const server = setupServer(
  http.post("/api/v1/invoices/", async () => {
    return HttpResponse.json(MOCK_NEW_INVOICE, { status: 201 });
  }),
  // useCustomers expects a plain array (see useCustomers.ts — res.data as CustomerListItem[])
  http.get("/api/v1/customers/", () =>
    HttpResponse.json([
      {
        id: "c-00000001",
        tenant_id: "t-00000001",
        type: "company",
        display_name: "Acme Electric",
        first_name: null,
        last_name: null,
        company_name: "Acme Electric",
        email: null,
        mobile_phone: null,
      },
    ]),
  ),
  http.get("/api/v1/customers/:customerId/sites", () =>
    HttpResponse.json([
      {
        id: "s-00000001",
        customer_id: "c-00000001",
        name: "Main Site",
        address: null,
        is_active: true,
      },
    ]),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(): AuthContextValue {
  const user: PilotUser = {
    id: "u-00000001",
    email: "test@pilot.example.com",
    role: "owner",
    tenantId: "t-00000001",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue()}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InvoiceBuilderPage — save", () => {
  it("1. validation blocks save when customer not selected — shows error message", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    // Click Save as Draft without selecting customer/site
    const saveButtons = screen.getAllByRole("button", {
      name: /Save as Draft/i,
    });
    fireEvent.click(saveButtons[0]);
    await waitFor(() => {
      expect(screen.getByText(/Please select a customer/i)).toBeInTheDocument();
    });
    // No POST should have been made
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("2. default billing_mode is 'line_item' — Select line items toggle visible", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    // billing_mode should default to line_item
    expect(
      screen.getByRole("button", { name: /Select line items/i }),
    ).toBeInTheDocument();
    // The Progress billing toggle is also present
    expect(
      screen.getByRole("button", { name: /Progress billing/i }),
    ).toBeInTheDocument();
  });

  it("3. on POST 412, TaxSetupSubFlowModal is not open at render time (pre-condition)", async () => {
    const Wrapper = createWrapper();
    server.use(
      http.post("/api/v1/invoices/", () =>
        HttpResponse.json(
          {
            detail:
              "Tax jurisdiction not configured. Please configure tax settings before creating invoices.",
          },
          { status: 412 },
        ),
      ),
    );
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    // Modal should not be open before any save attempt
    expect(
      screen.queryByRole("dialog", { name: /Tax Setup/i }),
    ).not.toBeInTheDocument();
    // Clicking without customer triggers validation, not 412
    const saveButtons = screen.getAllByRole("button", {
      name: /Save as Draft/i,
    });
    fireEvent.click(saveButtons[0]);
    await waitFor(() => {
      expect(screen.getByText(/Please select a customer/i)).toBeInTheDocument();
    });
  });

  it("4. Preview Invoice button is disabled (deferred per design doc §G)", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    const previewBtn = screen.getByRole("button", { name: /Preview Invoice/i });
    expect(previewBtn).toBeDisabled();
    expect(previewBtn.title).toMatch(/coming soon/i);
  });
});
