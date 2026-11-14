/**
 * Invoices integration tests — BETA-B3
 *
 * Location: apps/web/__tests__/batch_beta_v1_b3/invoices.test.tsx
 *
 * Tests the /invoices page: happy path, status filter, Load More, tech RoleGate, row links.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InvoicesPage } from "../../src/features/invoices/components/InvoicesPage";

// FE-B29: InvoicesPage now uses useRouter to navigate to /invoices/new
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("../../src/features/invoices/hooks/useInvoices", () => ({
  useInvoices: vi.fn(),
  INVOICES_QUERY_KEY: (opts: object) => ["invoices", opts],
}));

// FE-B22: InvoicesPage now uses useCreateInvoice
vi.mock("../../src/features/invoices/hooks/useCreateInvoice", () => ({
  useCreateInvoice: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

import { useInvoices } from "../../src/features/invoices/hooks/useInvoices";

const MOCK_RESPONSE = {
  items: [
    {
      id: "inv-001",
      invoice_number: "INV-2024-001",
      customer_id: "c-001",
      site_id: "s-001",
      status_id: "st-001",
      status_code: "sent",
      issued_at: "2024-01-15T00:00:00Z",
      due_at: "2024-02-15T00:00:00Z",
    },
    {
      id: "inv-002",
      invoice_number: "INV-2024-002",
      customer_id: "c-002",
      site_id: "s-002",
      status_id: "st-002",
      status_code: "paid",
      issued_at: "2024-01-20T00:00:00Z",
      due_at: "2024-02-20T00:00:00Z",
    },
  ],
  total: 2,
  limit: 50,
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
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function Wrapper({
  role,
  children,
}: {
  role: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        <NotificationQueueProvider>{children}</NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("/invoices integration", () => {
  beforeEach(() => {
    vi.mocked(useInvoices).mockReset();
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);
  });

  it("happy path — list renders for owner", () => {
    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText("INV-2024-001")).toBeTruthy();
    expect(screen.getByText("INV-2024-002")).toBeTruthy();
  });

  it("status filter pill 'Sent' is clickable", () => {
    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    const sentPill = screen.getByRole("button", { name: "Sent" });
    expect(sentPill).toBeTruthy();
    fireEvent.click(sentPill);
    // After click, useInvoices would be called with { status: "sent" } — pill is active
    expect(sentPill).toBeTruthy();
  });

  it("PilotPaginator appears when total > limit (UI-FIX-1C: replaces Load More)", () => {
    // 120 total, 50 per page → paginator shows (50 items loaded, 120 total)
    const fullPage = {
      items: Array.from({ length: 50 }, (_, i) => ({
        id: `inv-${i}`,
        invoice_number: `INV-${i}`,
        customer_id: `c-${i}`,
        site_id: `s-${i}`,
        status_id: `st-${i}`,
        status_code: "sent",
        issued_at: null,
        due_at: null,
      })),
      total: 120,
      limit: 50,
      offset: 0,
    };

    vi.mocked(useInvoices).mockReturnValue({
      data: fullPage,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    // Load More is gone — PilotPaginator renders when total > limit
    expect(screen.getByTestId("pilot-paginator")).toBeTruthy();
  });

  it("Load More button absent when items.length < PAGE_SIZE", () => {
    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    // Only 2 items, < 50 PAGE_SIZE
    expect(screen.queryByRole("button", { name: /load more/i })).toBeNull();
  });

  it("tech role — RoleGate blocks ALL invoices content (absent from DOM)", () => {
    const { container } = render(<InvoicesPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(container.textContent).toBe("");
    expect(screen.queryByText("INV-2024-001")).toBeNull();
  });

  it("invoice number links navigate to /invoices/[id]", () => {
    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    const link = screen.getByRole("link", { name: "INV-2024-001" });
    expect(link.getAttribute("href")).toBe("/invoices/inv-001");
  });

  it("empty state when API returns empty items", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByRole("heading", { name: /no invoices/i })).toBeTruthy();
  });

  it("error state when API returns error", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText(/could not load invoices/i)).toBeTruthy();
  });
});
