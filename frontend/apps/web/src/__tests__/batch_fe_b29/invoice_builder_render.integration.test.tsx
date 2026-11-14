/**
 * FE-B29 Integration — Invoice Builder Render
 *
 * Location: apps/web/src/__tests__/batch_fe_b29/invoice_builder_render.integration.test.tsx
 *
 * Tests:
 * 1. Page renders without crashing — "New Invoice" heading visible
 * 2. All section cards visible: Customer & Site, Billing Mode, Line Items, Payment Terms, Notes
 * 3. RoleGate: tech role should NOT see the invoice builder
 * 4. Cancel button triggers router.back()
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
  beforeEach,
} from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser } from "@pilot/ui/auth";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Navigation mock ───────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  usePathname: () => "/invoices/new",
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
beforeEach(() => {
  mockPush.mockClear();
  mockBack.mockClear();
});

// ── MSW ───────────────────────────────────────────────────────────────────────
// useCustomers expects a plain array (res.data as CustomerListItem[]) — NOT {items, total}

const server = setupServer(
  http.get("/api/v1/customers/", () => HttpResponse.json([])),
  http.get("/api/v1/customers/:customerId/sites", () => HttpResponse.json([])),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeUser(role: "owner" | "technician"): PilotUser {
  return {
    id: "u-00000001",
    email: "test@pilot.example.com",
    role,
    tenantId: "t-00000001",
    displayName: "Test User",
    accessToken: "mock-token",
  };
}

function makeAuthValue(role: "owner" | "technician"): AuthContextValue {
  return {
    user: makeUser(role),
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

// ── Query client wrapper ───────────────────────────────────────────────────────

function createWrapper(role: "owner" | "technician" = "owner") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue(role)}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InvoiceBuilderPage — render", () => {
  it("1. renders without crashing — 'New Invoice' heading visible", () => {
    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    expect(
      screen.getByRole("heading", { name: /New Invoice/i }),
    ).toBeInTheDocument();
  });

  it("2. all section cards visible: Customer & Site, Billing Mode, Line Items, Payment Terms, Notes", () => {
    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    expect(
      screen.getByRole("heading", { name: /Customer & Site/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Billing Mode/i }),
    ).toBeInTheDocument();
    // "Line Items" appears in section heading
    const lineItemHeadings = screen.getAllByText(/Line Items/i);
    expect(lineItemHeadings.length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: /Payment Terms/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /^Notes$/i }),
    ).toBeInTheDocument();
  });

  it("3. RoleGate: tech role should NOT see the invoice builder form", () => {
    const Wrapper = createWrapper("technician");
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    // Tech role does not have invoices.create permission — heading should not appear
    expect(
      screen.queryByRole("heading", { name: /New Invoice/i }),
    ).not.toBeInTheDocument();
  });

  it("4. Cancel button triggers router.back()", () => {
    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(mockBack).toHaveBeenCalledTimes(1);
  });
});
