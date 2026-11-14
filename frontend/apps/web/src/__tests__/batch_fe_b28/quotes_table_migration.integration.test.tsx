/**
 * FE-B28 — QuotesPage TanStack Table migration integration test
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/quotes_table_migration.integration.test.tsx
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
import { QuotesPage } from "@/features/quotes/components/QuotesPage";

vi.mock("next/navigation", () => ({
  usePathname: () => "/quotes",
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
        <QuotesPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("QuotesPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Quotes")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Quote #")).toBeInTheDocument();
      // "Customer" appears in filter label + column header — use getAllByText
      expect(screen.getAllByText("Customer").length).toBeGreaterThanOrEqual(1);
      // "Status" appears in filter dropdown label + column header
      expect(screen.getAllByText("Status").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Total")).toBeInTheDocument();
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });
  });

  it("renders status filter dropdown (UI-FIX-1C: pills replaced with select)", async () => {
    renderPage();
    await waitFor(() => {
      // UI-FIX-1C: status filter is now a <select> dropdown, not pills
      const statusSelect = screen.getByLabelText("Filter by status");
      expect(statusSelect).toBeInTheDocument();
    });
  });
});
