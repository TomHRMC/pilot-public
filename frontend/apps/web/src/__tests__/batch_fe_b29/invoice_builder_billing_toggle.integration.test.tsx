/**
 * FE-B29 Integration — Invoice Builder Billing Mode Toggle
 *
 * Location: apps/web/src/__tests__/batch_fe_b29/invoice_builder_billing_toggle.integration.test.tsx
 *
 * Tests:
 * 1. Default mode is "Select line items" — checklist section visible
 * 2. Clicking "Progress billing (%)" toggle — % input appears
 * 3. In progress mode, typed % shows computed amount label
 * 4. Switching back to "Select line items" — custom line item button re-appears
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

function makeAuthValue(): AuthContextValue {
  const user: PilotUser = {
    id: "u-00000001",
    email: "test@pilot.example.com",
    role: "owner",
    tenantId: "t-00000001",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue()}>
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

describe("InvoiceBuilderPage — billing mode toggle", () => {
  it("1. default mode is 'Select line items' — both toggle buttons visible", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    expect(
      screen.getByRole("button", { name: /Select line items/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Progress billing/i }),
    ).toBeInTheDocument();
    // In line_item mode, the "Add custom line item" button is present
    expect(
      screen.getByRole("button", { name: /Add custom line item/i }),
    ).toBeInTheDocument();
  });

  it("2. clicking 'Progress billing (%)' toggle — % input appears", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /Progress billing/i }));
    expect(
      screen.getByRole("spinbutton", {
        name: /Progress billing percentage/i,
      }),
    ).toBeInTheDocument();
  });

  it("3. in progress mode, typing a % value shows the computed amount label", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /Progress billing/i }));
    const pctInput = screen.getByRole("spinbutton", {
      name: /Progress billing percentage/i,
    });
    fireEvent.change(pctInput, { target: { value: "50" } });
    // The computed amount label should appear (= $X.XX)
    expect(screen.getByText(/= \$/i)).toBeInTheDocument();
  });

  it("4. switching back to 'Select line items' — custom line item button re-appears", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });
    // Switch to progress
    fireEvent.click(screen.getByRole("button", { name: /Progress billing/i }));
    expect(
      screen.getByRole("spinbutton", {
        name: /Progress billing percentage/i,
      }),
    ).toBeInTheDocument();
    // Switch back to line_item
    fireEvent.click(screen.getByRole("button", { name: /Select line items/i }));
    // Progress % input should be gone, add custom line item button should be back
    expect(
      screen.queryByRole("spinbutton", {
        name: /Progress billing percentage/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Add custom line item/i }),
    ).toBeInTheDocument();
  });
});
