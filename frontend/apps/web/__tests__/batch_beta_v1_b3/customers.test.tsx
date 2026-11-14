/**
 * Customers integration tests — BETA-B3 / UI-FIX-1C update
 *
 * Location: apps/web/__tests__/batch_beta_v1_b3/customers.test.tsx
 *
 * UI-FIX-1C: useCustomers now returns PaginatedResult<CustomerListItem>.
 * Mock updated to return { items, total, limit, offset } shape.
 * Search input is now type="text" (not type="search") — aria-label used instead.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { CustomersPage } from "../../src/features/customers/components/CustomersPage";

vi.mock("../../src/features/customers/hooks/useCustomers", () => ({
  useCustomers: vi.fn(),
  CUSTOMERS_QUERY_KEY: (
    offset: number,
    limit: number,
    search?: string,
    status?: string,
  ) => ["customers", offset, limit, search ?? "", status ?? ""],
}));

// Mock CreateCustomerModal to avoid deep render in these tests
vi.mock("../../src/features/customers/components/CreateCustomerModal", () => ({
  CreateCustomerModal: ({ open }: { open: boolean; onClose: () => void }) =>
    open ? <div data-testid="create-customer-modal">Modal</div> : null,
}));

// PLP-FIX-4: CustomersPage now uses useSearchParams + useRouter for ?add=1
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
}));

import { useCustomers } from "../../src/features/customers/hooks/useCustomers";

const MOCK_CUSTOMERS = [
  {
    id: "c-001",
    tenant_id: "t-001",
    type: "residential",
    display_name: "Alice Smith",
    first_name: "Alice",
    last_name: "Smith",
    company_name: null,
    email: "alice@example.com",
    mobile_phone: null,
  },
  {
    id: "c-002",
    tenant_id: "t-001",
    type: "commercial",
    display_name: "Acme Corp",
    first_name: null,
    last_name: null,
    company_name: "Acme Corp",
    email: "info@acme.example.com",
    mobile_phone: null,
  },
];

/** Paginated shape — matches PaginatedResult<CustomerListItem> */
const MOCK_PAGINATED = {
  items: MOCK_CUSTOMERS,
  total: 2,
  limit: 25,
  offset: 0,
};

function makeContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthContext.Provider value={makeContext()}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("/customers integration", () => {
  beforeEach(() => {
    vi.mocked(useCustomers).mockReset();
  });

  it("happy path — list renders with all customers", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByText("Alice Smith")).toBeTruthy();
    expect(screen.getByText("Acme Corp")).toBeTruthy();
  });

  it("search input is present (server-side search — API filtering tested in FE-B18 MSW tests)", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    // UI-FIX-1C: search input is type="text" with aria-label
    expect(screen.getByLabelText("Search customers")).toBeTruthy();
  });

  it("empty state when API returns empty array", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: { items: [], total: 0, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByText(/no customers yet/i)).toBeTruthy();
  });

  it("error state when API returns error", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByText(/could not load customers/i)).toBeTruthy();
  });

  it("row links navigate to /customers/[id]", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    const link = screen.getByRole("link", { name: "Alice Smith" });
    expect(link.getAttribute("href")).toBe("/customers/c-001");
  });
});
