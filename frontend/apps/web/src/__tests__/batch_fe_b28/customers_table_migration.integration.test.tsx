/**
 * FE-B28 — CustomersPage TanStack Table migration integration test
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/customers_table_migration.integration.test.tsx
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { setupServer } from "msw/node";
import { handlers } from "../../mocks/handlers/index";
import { CustomersPage } from "@/features/customers/components/CustomersPage";

vi.mock("next/navigation", () => ({
  usePathname: () => "/customers",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
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

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
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

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthContext()}>
      <QueryClientProvider client={qc}>
        <CustomersPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("CustomersPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Customers")).toBeInTheDocument();
    });
  });

  it("renders correct column headers: Name, Type, Email", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Type")).toBeInTheDocument();
      expect(screen.getByText("Email")).toBeInTheDocument();
    });
  });

  it("renders customer data from MSW fixture", async () => {
    renderPage();
    await waitFor(() => {
      // MOCK_CUSTOMERS from customerHandlers.ts has "Smith Electrical"
      expect(screen.getByText("Smith Electrical")).toBeInTheDocument();
    });
  });

  it("renders search input (UI-FIX-1C: placeholder updated)", async () => {
    renderPage();
    await waitFor(() => {
      // UI-FIX-1C: placeholder text updated
      expect(
        screen.getByPlaceholderText("Search by name, email, phone…"),
      ).toBeInTheDocument();
    });
  });
});
