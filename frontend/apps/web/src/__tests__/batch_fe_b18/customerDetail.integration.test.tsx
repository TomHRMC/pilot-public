/**
 * FE-B18 Integration — Customer Detail
 *
 * Location: apps/web/src/__tests__/batch_fe_b18/customerDetail.integration.test.tsx
 *
 * Tests the CustomerOverviewTab and SiteListPanel using MSW handlers.
 * Validates that "coming soon" strings are eliminated.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import {
  customerHandlers,
  MOCK_CUSTOMERS,
  MOCK_SITES,
} from "@/mocks/handlers/customerHandlers";
import { CustomerOverviewTab } from "@/features/customers/components/CustomerOverviewTab";
import { SiteListPanel } from "@/features/customers/components/SiteListPanel";

// FE-B24: CustomerOverviewTab now uses useRouter for delete navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/customers/c-1",
  useSearchParams: () => new URLSearchParams(),
}));

// Per-test MSW server — isolated from global handler set
const server = setupServer(...customerHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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

const CUSTOMER_ID = MOCK_CUSTOMERS[0].id; // Smith Electrical

describe("FE-B18 customerDetail integration — CustomerOverviewTab", () => {
  it('does not render "coming soon" text', async () => {
    render(<CustomerOverviewTab customerId={CUSTOMER_ID} />, {
      wrapper: Wrapper,
    });

    // Wait for data to load
    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    // Verify no "coming soon" string exists in DOM
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });

  it("shows customer name in overview", async () => {
    render(<CustomerOverviewTab customerId={CUSTOMER_ID} />, {
      wrapper: Wrapper,
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });
  });

  it("shows customer email from MSW fixture", async () => {
    render(<CustomerOverviewTab customerId={CUSTOMER_ID} />, {
      wrapper: Wrapper,
    });

    await waitFor(() => {
      expect(screen.getByText(MOCK_CUSTOMERS[0].email!)).toBeInTheDocument();
    });
  });

  it("Edit Customer button visible for owner", async () => {
    render(<CustomerOverviewTab customerId={CUSTOMER_ID} />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId("customer-edit-btn")).toBeInTheDocument();
  });

  it("Edit button toggles form into view for owner", async () => {
    render(<CustomerOverviewTab customerId={CUSTOMER_ID} />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("customer-edit-btn"));

    // Edit form should appear
    await waitFor(() => {
      expect(screen.getByText(/edit customer/i)).toBeInTheDocument();
    });
  });

  it("Edit Customer button hidden for tech", async () => {
    render(<CustomerOverviewTab customerId={CUSTOMER_ID} />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    expect(screen.queryByTestId("customer-edit-btn")).not.toBeInTheDocument();
  });
});

describe("FE-B18 customerDetail integration — SiteListPanel", () => {
  it('does not render "coming soon" text', async () => {
    render(<SiteListPanel customerId={CUSTOMER_ID} />, {
      wrapper: Wrapper,
    });

    await waitFor(() => {
      expect(screen.getByText(MOCK_SITES[0].name!)).toBeInTheDocument();
    });

    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });

  it("renders sites from MSW fixture", async () => {
    render(<SiteListPanel customerId={CUSTOMER_ID} />, {
      wrapper: Wrapper,
    });

    // MOCK_SITES[0] and [1] are both for CUSTOMER_ID (c-00000001-...)
    await waitFor(() => {
      expect(screen.getByText(MOCK_SITES[0].name!)).toBeInTheDocument();
    });
    expect(screen.getByText(MOCK_SITES[1].name!)).toBeInTheDocument();
  });

  it("Add Site button visible for owner", async () => {
    render(<SiteListPanel customerId={CUSTOMER_ID} />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText(MOCK_SITES[0].name!)).toBeInTheDocument();
    });

    expect(screen.getByTestId("add-site-btn")).toBeInTheDocument();
  });

  it("Add Site button hidden for tech", async () => {
    render(<SiteListPanel customerId={CUSTOMER_ID} />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    await waitFor(() => {
      expect(screen.getByText(MOCK_SITES[0].name!)).toBeInTheDocument();
    });

    expect(screen.queryByTestId("add-site-btn")).not.toBeInTheDocument();
  });
});
