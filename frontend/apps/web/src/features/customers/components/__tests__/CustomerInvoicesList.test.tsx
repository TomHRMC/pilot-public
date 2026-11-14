/**
 * CustomerInvoicesList unit tests — UI-FIX-2D
 *
 * Location: apps/web/src/features/customers/components/__tests__/CustomerInvoicesList.test.tsx
 *
 * Pattern: vi.mock the useInvoices hook (same as CustomersPage pattern).
 * No apiClient calls — no auth token needed.
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CustomerInvoicesList } from "../CustomerInvoicesList";

vi.mock("next/navigation", () => ({
  usePathname: () => "/customers/cust-1/invoices",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("../../../invoices/hooks/useInvoices", () => ({
  useInvoices: vi.fn(),
  INVOICES_QUERY_KEY: (opts: object) => ["invoices", opts],
}));

import { useInvoices } from "../../../invoices/hooks/useInvoices";

const MOCK_INVOICES = [
  {
    id: "inv-00000001-0000-0000-0000-000000000001",
    invoice_number: "INV-20260616-0001",
    customer_id: "cust-1",
    customer_name: "Apex Commercial LLC",
    site_id: "s-1",
    status_id: "st-issued",
    status_code: "issued",
    issued_at: "2026-06-16T00:00:00Z",
    due_at: "2027-06-30T00:00:00Z", // future — not overdue
    total_cents: 57914,
  },
  {
    id: "inv-00000003-0000-0000-0000-000000000003",
    invoice_number: "INV-20260601-0003",
    customer_id: "cust-1",
    customer_name: "Apex Commercial LLC",
    site_id: "s-1",
    status_id: "st-draft",
    status_code: "draft",
    issued_at: null,
    due_at: null,
    total_cents: null,
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

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const CUST_ID = "cust-1";

describe("CustomerInvoicesList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders invoice rows from mocked hook data", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: MOCK_INVOICES, total: 2, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    expect(screen.getByText("INV-20260616-0001")).toBeInTheDocument();
    expect(screen.getByText("INV-20260601-0003")).toBeInTheDocument();
  });

  it("does NOT render customer search input", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: MOCK_INVOICES, total: 2, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    // Customer search input must not be present — locked to customerId
    expect(
      screen.queryByPlaceholderText(/search by customer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/search invoices by customer name/i),
    ).not.toBeInTheDocument();
  });

  it("renders status pills and Overdue Only toggle", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: MOCK_INVOICES, total: 2, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    expect(
      screen.getByTestId("customer-invoices-overdue-toggle"),
    ).toBeInTheDocument();
    expect(screen.getByText("Paid")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Overdue Only")).toBeInTheDocument();
  });

  it("+ New Invoice link includes ?customer_id= param", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: MOCK_INVOICES, total: 2, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    const newInvoiceLink = screen.getByTestId("customer-invoices-new-btn");
    expect(newInvoiceLink).toHaveAttribute(
      "href",
      `/invoices/new?customer_id=${CUST_ID}`,
    );
  });

  it("renders empty state when no invoices returned", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    expect(screen.getAllByText(/no invoices/i).length).toBeGreaterThan(0);
  });

  it("renders loading state", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    expect(screen.getAllByText(/loading invoices/i).length).toBeGreaterThan(0);
  });

  it("renders error state on failure", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as never);

    renderWithQueryClient(<CustomerInvoicesList customerId={CUST_ID} />);
    expect(screen.getByText(/could not load invoices/i)).toBeInTheDocument();
  });
});
