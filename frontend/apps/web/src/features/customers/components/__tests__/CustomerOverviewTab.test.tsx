/**
 * CustomerOverviewTab unit tests — FE-B18
 *
 * Location: apps/web/src/features/customers/components/__tests__/CustomerOverviewTab.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { CustomerOverviewTab } from "../CustomerOverviewTab";

// FE-B24: CustomerOverviewTab now uses useRouter for navigation after delete
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/customers/c-001",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock hooks
vi.mock("../../hooks/useCustomer", () => ({
  useCustomer: vi.fn(),
  CUSTOMER_QUERY_KEY: (id: string | undefined) => ["customer", id],
}));
vi.mock("../../hooks/useUpdateCustomer", () => ({
  useUpdateCustomer: vi.fn(),
}));
// FE-B24: mock useDeleteCustomer to prevent real API calls in unit tests
vi.mock("../../hooks/useDeleteCustomer", () => ({
  useDeleteCustomer: () => ({
    mutate: vi.fn(),
    isPending: false,
    reset: vi.fn(),
  }),
}));

import { useCustomer } from "../../hooks/useCustomer";
import { useUpdateCustomer } from "../../hooks/useUpdateCustomer";

const MOCK_CUSTOMER = {
  id: "c-001",
  tenant_id: "t-001",
  type: "company",
  display_name: "Smith Electrical",
  first_name: null,
  last_name: null,
  company_name: "Smith Electrical LLC",
  email: "smith@example.com",
  mobile_phone: "5551234567",
  is_active: true,
  taxability_code: null,
  sms_opted_out: false,
  sms_opt_out_at: null,
  sms_opt_in_consent: true,
  sms_opt_in_at: "2024-01-15T10:00:00Z",
  sms_opt_in_source: "manual",
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
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
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

describe("CustomerOverviewTab", () => {
  beforeEach(() => {
    // clearAllMocks FIRST so subsequent mockReturnValue calls take effect
    vi.clearAllMocks();
    vi.mocked(useUpdateCustomer).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("renders LoadingState while fetching", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getAllByText(/loading customer/i).length).toBeGreaterThan(0);
  });

  it("renders ErrorState on API failure", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText(/could not load customer/i)).toBeTruthy();
  });

  it("shows customer name and email from mock data", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
    expect(screen.getByText("smith@example.com")).toBeTruthy();
  });

  it("shows SMS opted in badge when opted in", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_CUSTOMER, // sms_opted_out: false, sms_opt_in_consent: true
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText(/opted in/i)).toBeTruthy();
  });

  it("shows SMS opted out badge when opted out", () => {
    const optedOutCustomer = {
      ...MOCK_CUSTOMER,
      sms_opted_out: true,
      sms_opt_out_at: "2024-03-10T14:30:00Z",
      sms_opt_in_consent: false,
    };
    vi.mocked(useCustomer).mockReturnValue({
      data: optedOutCustomer,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, { wrapper: Wrapper });
    // Use getAllByText since both the badge "Opted out" and the date span "(opted out ...)" match
    expect(screen.getAllByText(/opted out/i).length).toBeGreaterThan(0);
  });

  it("Edit button visible for owner", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByTestId("customer-edit-btn")).toBeTruthy();
  });

  it("Edit button hidden for tech", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(screen.queryByTestId("customer-edit-btn")).toBeNull();
  });

  it("shows company name when type=company", () => {
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<CustomerOverviewTab customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText("Smith Electrical LLC")).toBeTruthy();
  });
});
