/**
 * SiteListPanel unit tests — FE-B18
 *
 * Location: apps/web/src/features/customers/components/__tests__/SiteListPanel.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { SiteListPanel } from "../SiteListPanel";

// Mock hooks
vi.mock("../../hooks/useCustomerSites", () => ({
  useCustomerSites: vi.fn(),
  CUSTOMER_SITES_QUERY_KEY: (id: string | undefined) => ["customer-sites", id],
}));
vi.mock("../../hooks/useCreateSite", () => ({
  useCreateSite: vi.fn(),
}));
vi.mock("../../hooks/useUpdateSite", () => ({
  useUpdateSite: vi.fn(),
}));
vi.mock("../../hooks/useCustomer", () => ({
  useCustomer: vi.fn(),
  CUSTOMER_QUERY_KEY: (id: string | undefined) => ["customer", id],
}));

import { useCustomerSites } from "../../hooks/useCustomerSites";
import { useCreateSite } from "../../hooks/useCreateSite";
import { useUpdateSite } from "../../hooks/useUpdateSite";
import { useCustomer } from "../../hooks/useCustomer";

const MOCK_SITES = [
  {
    id: "site-001",
    tenant_id: "t-001",
    customer_id: "c-001",
    name: "Main Office",
    notes: "Primary commercial location",
    jurisdiction_code: "TX-AUSTIN",
    is_active: true,
    site_type: "commercial" as const,
    address: {
      id: "addr-001",
      line1: "123 Main St",
      line2: null,
      line3: null,
      city: "Austin",
      state: "TX",
      postal_code: "78701",
      country: "US",
      latitude: null,
      longitude: null,
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
  },
  {
    id: "site-002",
    tenant_id: "t-001",
    customer_id: "c-001",
    name: "Warehouse",
    notes: null,
    jurisdiction_code: null,
    is_active: true,
    site_type: null,
    address: null,
  },
];

const MOCK_COMPANY_CUSTOMER = {
  id: "c-001",
  tenant_id: "t-001",
  type: "company",
  display_name: "Acme Corp",
  first_name: null,
  last_name: null,
  company_name: "Acme Corp LLC",
  email: null,
  mobile_phone: null,
  is_active: true,
  taxability_code: null,
  sms_opted_out: false,
  sms_opt_out_at: null,
  sms_opt_in_consent: false,
  sms_opt_in_at: null,
  sms_opt_in_source: null,
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

describe("SiteListPanel", () => {
  beforeEach(() => {
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_COMPANY_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);
    vi.mocked(useCreateSite).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.mocked(useUpdateSite).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
    vi.clearAllMocks();
  });

  it("renders LoadingState while fetching", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getAllByText(/loading sites/i).length).toBeGreaterThan(0);
  });

  it("renders ErrorState on API failure", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText(/could not load sites/i)).toBeTruthy();
  });

  it("renders EmptyState when no sites", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText(/no sites yet/i)).toBeTruthy();
  });

  it("renders site cards with name from mock data", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText("Main Office")).toBeTruthy();
    expect(screen.getByText("Warehouse")).toBeTruthy();
  });

  it("renders site address from mock data", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByText(/123 Main St/)).toBeTruthy();
  });

  it('"Add Site" button visible for owner', () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByTestId("add-site-btn")).toBeTruthy();
  });

  it('"Add Site" button hidden for tech', () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(screen.queryByTestId("add-site-btn")).toBeNull();
  });

  it('"Edit" button per site visible for owner', () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    // Should have edit button for each site
    expect(screen.getByTestId("edit-site-btn-site-001")).toBeTruthy();
    expect(screen.getByTestId("edit-site-btn-site-002")).toBeTruthy();
  });

  it('"Edit" button hidden for tech', () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_COMPANY_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(screen.queryByTestId("edit-site-btn-site-001")).toBeNull();
  });

  // CUST-UI-B1: site_type chip tests
  it("shows site_type chip for a site with site_type='commercial'", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_COMPANY_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    expect(screen.getByTestId("site-type-chip-site-001")).toBeTruthy();
    expect(screen.getByTestId("site-type-chip-site-001").textContent).toBe(
      "commercial",
    );
  });

  it("omits site_type chip when site_type is null", () => {
    vi.mocked(useCustomerSites).mockReturnValue({
      data: MOCK_SITES,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);
    vi.mocked(useCustomer).mockReturnValue({
      data: MOCK_COMPANY_CUSTOMER,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<SiteListPanel customerId="c-001" />, { wrapper: Wrapper });
    // site-002 has site_type: null — chip should not exist
    expect(screen.queryByTestId("site-type-chip-site-002")).toBeNull();
  });
});
