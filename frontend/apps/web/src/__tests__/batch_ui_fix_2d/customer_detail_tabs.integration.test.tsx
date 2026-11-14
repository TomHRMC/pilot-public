/**
 * Integration tests — UI-FIX-2D: Customer Detail Jobs/Quotes/Invoices Tabs
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_2d/customer_detail_tabs.integration.test.tsx
 *
 * Pattern: vi.mock all 3 data hooks (same pattern as existing feature tests).
 * Tests verify component rendering, hidden customer search, and + New links.
 *
 * Rules:
 * - retry: false on QueryClient (Rule 14)
 * - vi.mock("next/navigation", ...) for web (Rule 17)
 * - Hook mocks prevent apiClient auth requirements in test env
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { CustomerJobsList } from "../../features/customers/components/CustomerJobsList";
import { CustomerQuotesList } from "../../features/customers/components/CustomerQuotesList";
import { CustomerInvoicesList } from "../../features/customers/components/CustomerInvoicesList";

vi.mock("next/navigation", () => ({
  usePathname: () => "/customers/cust-1",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("../../features/jobs/hooks/useJobs", () => ({
  useJobs: vi.fn(),
  JOBS_QUERY_KEY: (opts: object) => ["jobs", opts ?? {}],
}));

// PLP-FIX-2: mock JobFormModal to avoid its hook dependencies
vi.mock("../../features/jobs/components/JobFormModal", () => ({
  JobFormModal: ({
    open,
    prefilledCustomerId,
  }: {
    open: boolean;
    prefilledCustomerId?: string;
  }) =>
    open
      ? React.createElement(
          "div",
          { "data-testid": "mock-job-form-modal" },
          `prefilledCustomerId=${prefilledCustomerId}`,
        )
      : null,
}));

vi.mock("../../features/quotes/hooks/useQuotes", () => ({
  useQuotes: vi.fn(),
  QUOTES_QUERY_KEY: (opts: object) => ["quotes", opts],
}));

vi.mock("../../features/invoices/hooks/useInvoices", () => ({
  useInvoices: vi.fn(),
  INVOICES_QUERY_KEY: (opts: object) => ["invoices", opts],
}));

import { useJobs } from "../../features/jobs/hooks/useJobs";
import { useQuotes } from "../../features/quotes/hooks/useQuotes";
import { useInvoices } from "../../features/invoices/hooks/useInvoices";

const CUST_ID = "cust-abc-123";

const MOCK_JOBS_DATA = [
  {
    id: "job-1",
    tenant_id: "t-1",
    customer_id: CUST_ID,
    site_id: "s-1",
    status_id: "st-scheduled",
    status_code: "scheduled",
    customer_name: "Apex Commercial LLC",
    job_number: "JOB-000001",
    scheduled_start_at: "2026-07-24T09:00:00Z",
    scheduled_end_at: null,
    estimated_duration_minutes: 240,
    recurrence_rule_id: null,
  },
];

const MOCK_QUOTES_DATA = [
  {
    id: "q-1",
    tenant_id: "t-1",
    customer_id: CUST_ID,
    customer_name: "Apex Commercial LLC",
    site_id: "s-1",
    status_id: "st-draft",
    status_code: "draft",
    quote_number: "QUO-000001",
    title: "Panel Upgrade for Apex",
    created_at: "2026-07-01T00:00:00Z",
    subtotal_cents: 185000,
    tax_cents: 14800,
    total_cents: 199800,
  },
];

const MOCK_INVOICES_DATA = [
  {
    id: "inv-1",
    invoice_number: "INV-20260616-0001",
    customer_id: CUST_ID,
    customer_name: "Apex Commercial LLC",
    site_id: "s-1",
    status_id: "st-issued",
    status_code: "issued",
    issued_at: "2026-06-16T00:00:00Z",
    due_at: "2027-06-30T00:00:00Z",
    total_cents: 57914,
  },
];

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

// PLP-FIX-2: AuthContext needed for RoleGate in CustomerJobsList
function makeAuthValue(
  role: "owner" | "technician" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u-00000001",
      email: "test@pilot.example.com",
      role,
      tenantId: "t-00000001",
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

function wrap(ui: React.ReactElement, role: "owner" | "technician" = "owner") {
  const qc = makeQueryClient();
  return render(
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("UI-FIX-2D — Customer Detail Tab Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Jobs Tab ──────────────────────────────────────────────────────────────

  it("Jobs tab: renders jobs from mocked hook (no placeholder text)", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS_DATA, total: 1, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerJobsList customerId={CUST_ID} />);
    expect(screen.getByText("JOB-000001")).toBeInTheDocument();
    // Ensure no old placeholder text
    expect(
      screen.queryByText(/full job details for this customer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/will be available in the jobs module/i),
    ).not.toBeInTheDocument();
  });

  it("Jobs tab: does NOT render customer search input", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS_DATA, total: 1, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerJobsList customerId={CUST_ID} />);
    expect(
      screen.queryByPlaceholderText(/search by customer/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("job-customer-search")).not.toBeInTheDocument();
  });

  // ── Quotes Tab ────────────────────────────────────────────────────────────

  it("Quotes tab: renders quotes from mocked hook (no placeholder text)", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES_DATA, total: 1, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerQuotesList customerId={CUST_ID} />);
    expect(screen.getByText("Panel Upgrade for Apex")).toBeInTheDocument();
    expect(
      screen.queryByText(/quote history for this customer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/once the quote builder is complete/i),
    ).not.toBeInTheDocument();
  });

  it("Quotes tab: does NOT render customer search input", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES_DATA, total: 1, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerQuotesList customerId={CUST_ID} />);
    expect(
      screen.queryByPlaceholderText(/search by customer/i),
    ).not.toBeInTheDocument();
  });

  // ── Invoices Tab ──────────────────────────────────────────────────────────

  it("Invoices tab: renders invoices from mocked hook (no placeholder text)", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: MOCK_INVOICES_DATA, total: 1, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerInvoicesList customerId={CUST_ID} />);
    expect(screen.getByText("INV-20260616-0001")).toBeInTheDocument();
    expect(
      screen.queryByText(/invoice history for this customer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/will be available in the invoices module/i),
    ).not.toBeInTheDocument();
  });

  // ── New Entity Links ──────────────────────────────────────────────────────

  it("+ New Job button opens modal with prefilled customer (PLP-FIX-2)", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS_DATA, total: 1, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerJobsList customerId={CUST_ID} />);
    const newJobBtn = screen.getByTestId("customer-jobs-new-btn");
    // PLP-FIX-2: it's a button now, not an anchor — no href attribute
    expect(newJobBtn).not.toHaveAttribute("href");
    fireEvent.click(newJobBtn);
    expect(screen.getByTestId("mock-job-form-modal")).toBeInTheDocument();
    expect(screen.getByTestId("mock-job-form-modal").textContent).toContain(
      `prefilledCustomerId=${CUST_ID}`,
    );
  });

  it("+ New Quote link contains correct ?customer_id= param", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES_DATA, total: 1, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerQuotesList customerId={CUST_ID} />);
    const newQuoteLink = screen.getByTestId("customer-quotes-new-btn");
    expect(newQuoteLink).toHaveAttribute(
      "href",
      `/quotes/new?customer_id=${CUST_ID}`,
    );
  });

  it("+ New Invoice link contains correct ?customer_id= param", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: MOCK_INVOICES_DATA, total: 1, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    wrap(<CustomerInvoicesList customerId={CUST_ID} />);
    const newInvoiceLink = screen.getByTestId("customer-invoices-new-btn");
    expect(newInvoiceLink).toHaveAttribute(
      "href",
      `/invoices/new?customer_id=${CUST_ID}`,
    );
  });
});
