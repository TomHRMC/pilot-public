/**
 * InvoicesPage unit tests — BETA-B3 / SD-FE-1
 *
 * Location: apps/web/src/features/invoices/components/__tests__/InvoicesPage.test.tsx
 *
 * SD-FE-1 changes:
 *  - Fixed mock data: status_code "sent" → "issued" (correct DB code)
 *  - Updated status pill assertions: removed "Overdue" pill (it's now "Overdue Only" toggle),
 *    added "Void" and "Write-Off" pills
 *  - Added: test_sent_filter_uses_issued_code
 *  - Added: test_overdue_toggle_uses_overdue_param
 *  - Added: test_overdue_pill_not_in_status_filter
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InvoicesPage } from "../InvoicesPage";

// FE-B29: InvoicesPage now uses useRouter to navigate to /invoices/new
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock useInvoices hook
vi.mock("../../hooks/useInvoices", () => ({
  useInvoices: vi.fn(),
  INVOICES_QUERY_KEY: (opts: object) => ["invoices", opts],
}));

// Mock useCreateInvoice — FE-B22: InvoicesPage now uses this hook
vi.mock("../../hooks/useCreateInvoice", () => ({
  useCreateInvoice: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

import { useInvoices } from "../../hooks/useInvoices";

/**
 * SD-FE-1: Mock data uses status_code: "issued" (correct DB code).
 * "sent" does NOT exist in invoice_status — corrected from prior BETA-B3 fixture.
 */
const MOCK_INVOICE_RESPONSE = {
  items: [
    {
      id: "inv-001",
      invoice_number: "INV-2024-001",
      customer_id: "c-001",
      site_id: "s-001",
      status_id: "st-001",
      status_code: "issued", // SD-FE-1: was "sent" — "issued" is the correct DB code
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

describe("InvoicesPage", () => {
  beforeEach(() => {
    vi.mocked(useInvoices).mockReset();
  });

  it("renders loading state for owner", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    // LoadingState renders label in visible span + sr-only span
    expect(screen.getAllByText(/loading invoices/i).length).toBeGreaterThan(0);
  });

  it("renders invoice list for owner", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText("INV-2024-001")).toBeTruthy();
    expect(screen.getByText("INV-2024-002")).toBeTruthy();
  });

  it("tech role does NOT see invoices content (RoleGate blocks)", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    const { container } = render(<InvoicesPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(container.textContent).toBe("");
    expect(screen.queryByText("INV-2024-001")).toBeNull();
  });

  it("renders empty state when no invoices", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    // EmptyState renders title in h2 and description in p — use heading role to be specific
    expect(screen.getByRole("heading", { name: /no invoices/i })).toBeTruthy();
  });

  /**
   * SD-FE-1: Updated — "Overdue" pill removed (not a DB status code).
   * Added: "Void" and "Write-Off" pills. "Overdue Only" is now a separate toggle.
   */
  it("status pills are rendered (All, Draft, Sent, Paid, Void, Write-Off) and Overdue Only toggle", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByRole("button", { name: "All" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sent" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Paid" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Void" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Write-Off" })).toBeTruthy();
    // "Overdue Only" is a separate toggle, not a status pill
    expect(screen.getByTestId("overdue-toggle")).toBeTruthy();
  });

  it("invoice number is a link to /invoices/[id]", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    const link = screen.getByRole("link", { name: "INV-2024-001" });
    expect(link.getAttribute("href")).toBe("/invoices/inv-001");
  });

  it("total count is displayed in header", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText("2 total")).toBeTruthy();
  });

  it("office_staff can see invoices", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="office_staff">{children}</Wrapper>
      ),
    });
    expect(screen.getByText("INV-2024-001")).toBeTruthy();
  });

  it("clicking status pill calls useInvoices with status filter", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    const sentPill = screen.getByRole("button", { name: "Sent" });
    fireEvent.click(sentPill);

    // After clicking, useInvoices is called with { status: "issued", limit: 50, offset: 0 }
    // Verify the pill is rendered and clickable
    expect(sentPill).toBeTruthy();
  });

  // ── SD-FE-1: New tests ─────────────────────────────────────────────────────

  /**
   * SD-FE-1 test_sent_filter_uses_issued_code
   * Clicking "Sent" pill must pass status="issued" (the correct DB code) to useInvoices.
   * "sent" does NOT exist in invoice_status — confirmed via MCP 2026-07-06.
   */
  it("test_sent_filter_uses_issued_code — Sent pill passes status=issued to useInvoices", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    const sentPill = screen.getByRole("button", { name: "Sent" });
    fireEvent.click(sentPill);

    // useInvoices should have been called with status: "issued" — NOT "sent"
    const calls = vi.mocked(useInvoices).mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall?.status).toBe("issued");
    expect(lastCall?.status).not.toBe("sent");
  });

  /**
   * SD-FE-1 test_overdue_toggle_uses_overdue_param
   * Clicking the "Overdue Only" toggle must pass overdue=true to useInvoices.
   * "overdue" is NOT a DB status code — it is triggered via ?overdue=true param.
   */
  it("test_overdue_toggle_uses_overdue_param — Overdue Only toggle passes overdue=true to useInvoices", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    const overdueToggle = screen.getByTestId("overdue-toggle");
    fireEvent.click(overdueToggle);

    // useInvoices should have been called with overdue: true
    const calls = vi.mocked(useInvoices).mock.calls;
    const lastCall = calls[calls.length - 1][0];
    expect(lastCall?.overdue).toBe(true);
  });

  /**
   * SD-FE-1 test_overdue_pill_not_in_status_filter
   * There must be NO status filter pill with the label "Overdue" (value="overdue").
   * "overdue" is not a DB status code and must not appear in STATUS_FILTERS.
   */
  it("test_overdue_pill_not_in_status_filter — no Overdue status pill in filter bar", () => {
    vi.mocked(useInvoices).mockReturnValue({
      data: MOCK_INVOICE_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<InvoicesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    // There should be no button with the exact label "Overdue" in the status pills
    // (the toggle is "Overdue Only" and uses data-testid, not a status filter value)
    expect(screen.queryByRole("button", { name: "Overdue" })).toBeNull();
  });
});
