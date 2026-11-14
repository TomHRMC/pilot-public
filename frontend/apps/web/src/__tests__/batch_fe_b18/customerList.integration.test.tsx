/**
 * FE-B18 Integration — Customer List
 *
 * Location: apps/web/src/__tests__/batch_fe_b18/customerList.integration.test.tsx
 *
 * Tests the /customers list page with MSW handlers.
 * Uses per-file server setup (not shared global server).
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
} from "@/mocks/handlers/customerHandlers";
import { CustomersPage } from "@/features/customers/components/CustomersPage";

// PLP-FIX-4: CustomersPage now uses useSearchParams + useRouter for ?add=1
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
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

describe("FE-B18 customerList integration", () => {
  it("renders customer list with data from MSW", async () => {
    render(<CustomersPage />, { wrapper: Wrapper });

    // Wait for the first fixture customer to appear
    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(MOCK_CUSTOMERS[1].display_name),
    ).toBeInTheDocument();
    expect(
      screen.getByText(MOCK_CUSTOMERS[2].display_name),
    ).toBeInTheDocument();
  });

  it('"Add Customer" button visible for owner', async () => {
    render(<CustomersPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId("add-customer-btn")).toBeInTheDocument();
  });

  it('"Add Customer" button hidden for tech', async () => {
    render(<CustomersPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    expect(screen.queryByTestId("add-customer-btn")).not.toBeInTheDocument();
  });

  it("clicking Add Customer opens modal", async () => {
    render(<CustomersPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("add-customer-btn"));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("customer names are links to /customers/[id]", async () => {
    render(<CustomersPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(
        screen.getByText(MOCK_CUSTOMERS[0].display_name),
      ).toBeInTheDocument();
    });

    const link = screen.getByRole("link", {
      name: MOCK_CUSTOMERS[0].display_name,
    });
    expect(link.getAttribute("href")).toBe(
      `/customers/${MOCK_CUSTOMERS[0].id}`,
    );
  });
});
