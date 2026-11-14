/**
 * CustomerQuotesList unit tests — UI-FIX-2D
 *
 * Location: apps/web/src/features/customers/components/__tests__/CustomerQuotesList.test.tsx
 *
 * Pattern: vi.mock the useQuotes hook (same as CustomersPage pattern).
 * No apiClient calls — no auth token needed.
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CustomerQuotesList } from "../CustomerQuotesList";

vi.mock("next/navigation", () => ({
  usePathname: () => "/customers/cust-1/quotes",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("../../../quotes/hooks/useQuotes", () => ({
  useQuotes: vi.fn(),
  QUOTES_QUERY_KEY: (opts: object) => ["quotes", opts],
}));

import { useQuotes } from "../../../quotes/hooks/useQuotes";

const MOCK_QUOTES = [
  {
    id: "q-00000001-0000-0000-0000-000000000001",
    tenant_id: "t-1",
    customer_id: "cust-1",
    customer_name: "Apex Commercial LLC",
    site_id: "s-1",
    status_id: "st-1",
    status_code: "draft",
    quote_number: "QUO-000001",
    title: "Panel Upgrade Q1",
    created_at: "2026-07-01T00:00:00Z",
    subtotal_cents: 185000,
    tax_cents: 14800,
    total_cents: 199800,
  },
  {
    id: "q-00000002-0000-0000-0000-000000000002",
    tenant_id: "t-1",
    customer_id: "cust-1",
    customer_name: "Apex Commercial LLC",
    site_id: "s-1",
    status_id: "st-2",
    status_code: "sent",
    quote_number: "QUO-000002",
    title: "Rewire Master Bedroom",
    created_at: "2026-07-10T00:00:00Z",
    subtotal_cents: 320000,
    tax_cents: 25600,
    total_cents: 345600,
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

describe("CustomerQuotesList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders quote rows from mocked hook data", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    expect(screen.getByText("Panel Upgrade Q1")).toBeInTheDocument();
    expect(screen.getByText("Rewire Master Bedroom")).toBeInTheDocument();
  });

  it("does NOT render customer search input", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    // Customer search input must not be present — locked to customerId
    expect(
      screen.queryByPlaceholderText(/search by customer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/search by customer/i),
    ).not.toBeInTheDocument();
  });

  it("renders title search input and status dropdown", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    expect(
      screen.getByTestId("customer-quotes-title-search"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("customer-quotes-status-select"),
    ).toBeInTheDocument();
  });

  it("+ New Quote link includes ?customer_id= param", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: MOCK_QUOTES, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    const newQuoteLink = screen.getByTestId("customer-quotes-new-btn");
    expect(newQuoteLink).toHaveAttribute(
      "href",
      `/quotes/new?customer_id=${CUST_ID}`,
    );
  });

  it("renders empty state when no quotes returned", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: [], total: 0, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    expect(screen.getAllByText(/no quotes/i).length).toBeGreaterThan(0);
  });

  it("renders loading state", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    expect(screen.getAllByText(/loading quotes/i).length).toBeGreaterThan(0);
  });

  it("renders error state on failure", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as never);

    renderWithQueryClient(<CustomerQuotesList customerId={CUST_ID} />);
    expect(screen.getByText(/could not load quotes/i)).toBeInTheDocument();
  });
});
