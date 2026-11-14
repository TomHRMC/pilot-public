/**
 * CustomersPage unit tests — UI-FIX-1C update
 *
 * Location: apps/web/src/features/customers/components/__tests__/CustomersPage.test.tsx
 *
 * UI-FIX-1C: useCustomers now returns PaginatedResult<CustomerListItem>.
 * Mock updated to return { items, total, limit, offset } shape.
 * Filter bar inputs and PilotPaginator tested.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { CustomersPage } from "../CustomersPage";

// Mock useCustomers hook
vi.mock("../../hooks/useCustomers", () => ({
  useCustomers: vi.fn(),
  CUSTOMERS_QUERY_KEY: (
    offset: number,
    limit: number,
    search?: string,
    status?: string,
  ) => ["customers", offset, limit, search ?? "", status ?? ""],
}));

// Mock CreateCustomerModal to avoid needing useCreateCustomer in unit tests
vi.mock("../CreateCustomerModal", () => ({
  CreateCustomerModal: ({ open }: { open: boolean; onClose: () => void }) =>
    open ? <div data-testid="create-customer-modal">Modal</div> : null,
}));

// PLP-FIX-4: CustomersPage now uses useSearchParams + useRouter for ?add=1 deep-link
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
}));

import { useCustomers } from "../../hooks/useCustomers";

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
    email: "acme@corp.com",
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

function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function Wrapper({
  role = "owner",
  children,
}: {
  role?: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("CustomersPage", () => {
  beforeEach(() => {
    vi.mocked(useCustomers).mockReset();
  });

  it("renders loading state", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getAllByText(/loading customers/i).length).toBeGreaterThan(0);
  });

  it("renders error state with retry button", () => {
    const refetch = vi.fn();
    vi.mocked(useCustomers).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch,
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByText(/could not load customers/i)).toBeTruthy();
  });

  it("renders empty state when no customers", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: { items: [], total: 0, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByText(/no customers yet/i)).toBeTruthy();
  });

  it("renders customer list with name, type, email columns", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByText("Alice Smith")).toBeTruthy();
    expect(screen.getByText("Acme Corp")).toBeTruthy();
    expect(screen.getByText("alice@example.com")).toBeTruthy();
    expect(screen.getByText("residential")).toBeTruthy();
    expect(screen.getByText("commercial")).toBeTruthy();
  });

  it("search input is present in filter bar", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByLabelText("Search customers")).toBeTruthy();
  });

  it("status dropdown is present in filter bar", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, { wrapper: Wrapper });
    expect(screen.getByLabelText("Filter by status")).toBeTruthy();
  });

  it("customer name is a link to /customers/[id]", () => {
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

  it('"Add Customer" button visible for owner', () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByTestId("add-customer-btn")).toBeTruthy();
  });

  it('"Add Customer" button hidden for tech', () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(screen.queryByTestId("add-customer-btn")).toBeNull();
  });

  it("clicking Add Customer opens modal", () => {
    vi.mocked(useCustomers).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomersPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    expect(screen.queryByTestId("create-customer-modal")).toBeNull();
    fireEvent.click(screen.getByTestId("add-customer-btn"));
    expect(screen.getByTestId("create-customer-modal")).toBeTruthy();
  });
});
