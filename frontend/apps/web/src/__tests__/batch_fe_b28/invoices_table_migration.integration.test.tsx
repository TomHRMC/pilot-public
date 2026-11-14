/**
 * FE-B28 — InvoicesPage TanStack Table migration integration test
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/invoices_table_migration.integration.test.tsx
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
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { setupServer } from "msw/node";
import { handlers } from "../../mocks/handlers/index";
import {
  InvoicesPage,
  isOverdue,
} from "@/features/invoices/components/InvoicesPage";

vi.mock("next/navigation", () => ({
  usePathname: () => "/invoices",
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
    <NotificationQueueProvider>
      <AuthContext.Provider value={makeAuthContext()}>
        <QueryClientProvider client={qc}>
          <InvoicesPage />
        </QueryClientProvider>
      </AuthContext.Provider>
    </NotificationQueueProvider>,
  );
}

describe("InvoicesPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Invoices")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Invoice #")).toBeInTheDocument();
      // UI-FIX-1C: "Customer" appears in both filter label and column header
      expect(screen.getAllByText("Customer").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Total")).toBeInTheDocument();
      expect(screen.getByText("Issued")).toBeInTheDocument();
      expect(screen.getByText("Due")).toBeInTheDocument();
    });
  });

  it("renders Overdue Only toggle button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("overdue-toggle")).toBeInTheDocument();
    });
  });

  it("renders status filter pills", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("All")).toBeInTheDocument();
      expect(screen.getByText("Paid")).toBeInTheDocument();
    });
  });
});

describe("isOverdue helper — FE-B28", () => {
  it("returns false for paid invoice", () => {
    expect(
      isOverdue({ due_at: "2020-01-01T00:00:00Z", status_code: "paid" }),
    ).toBe(false);
  });

  it("returns false for null due_at", () => {
    expect(isOverdue({ due_at: null, status_code: "issued" })).toBe(false);
  });

  it("returns true for past due issued invoice", () => {
    expect(
      isOverdue({ due_at: "2020-01-01T00:00:00Z", status_code: "issued" }),
    ).toBe(true);
  });
});
