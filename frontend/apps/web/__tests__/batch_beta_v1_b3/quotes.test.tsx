/**
 * Quotes integration tests — BETA-B3 / UI-FIX-1C update
 *
 * Location: apps/web/__tests__/batch_beta_v1_b3/quotes.test.tsx
 *
 * UI-FIX-1C: useQuotes now returns PaginatedResult<QuoteListItem>.
 * Status pills replaced with <select> dropdown — tests updated.
 * Mock updated to return { items, total, limit, offset } shape.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { QuotesPage } from "../../src/features/quotes/components/QuotesPage";

// FE-B19: QuotesPage now uses useRouter and useConvertQuote — mock both
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/quotes",
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("../../src/features/quotes/hooks/useConvertQuote", () => ({
  useConvertQuote: () => ({ mutate: vi.fn(), isPending: false }),
}));

// UI-FIX-1C: QUOTES_QUERY_KEY is now object-based
vi.mock("../../src/features/quotes/hooks/useQuotes", () => ({
  useQuotes: vi.fn(),
  QUOTES_QUERY_KEY: (options: Record<string, unknown>) => ["quotes", options],
}));

import { useQuotes } from "../../src/features/quotes/hooks/useQuotes";

const MOCK_QUOTES = [
  {
    id: "q-00000001-0000-0000-0000-000000000001",
    tenant_id: "t-001",
    customer_id: "c-001",
    customer_name: "Smith Electrical",
    site_id: "s-001",
    status_id: "st-001",
    status_code: "draft",
    subtotal_cents: 185000,
    tax_cents: 14800,
    total_cents: 199800,
  },
  {
    id: "q-00000002-0000-0000-0000-000000000002",
    tenant_id: "t-001",
    customer_id: "c-002",
    customer_name: "Johnson Services",
    site_id: "s-002",
    status_id: "st-002",
    status_code: "sent",
    subtotal_cents: 320000,
    tax_cents: 25600,
    total_cents: 345600,
  },
];

/** Paginated shape — matches PaginatedResult<QuoteListItem> */
function makePaginated(items: typeof MOCK_QUOTES) {
  return { items, total: items.length, limit: 25, offset: 0 };
}

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
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("/quotes integration", () => {
  beforeEach(() => {
    vi.mocked(useQuotes).mockReset();
    // UI-FIX-1C: useQuotes returns paginated shape
    vi.mocked(useQuotes).mockImplementation(({ status } = {}) => {
      const filtered = status
        ? MOCK_QUOTES.filter((q) => q.status_code === status)
        : MOCK_QUOTES;
      return {
        data: makePaginated(filtered),
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      } as never;
    });
  });

  it("happy path — list renders with MSW mock data for owner", () => {
    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
    expect(screen.getByText("Johnson Services")).toBeTruthy();
  });

  it("status filter dropdown exists (UI-FIX-1C: pills replaced with select)", () => {
    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    // UI-FIX-1C: Status is now a <select> dropdown, not pills
    const statusSelect = screen.getByLabelText("Filter by status");
    expect(statusSelect).toBeTruthy();
    // Select options include Draft and Sent
    expect(statusSelect).toHaveValue("");
  });

  it("status dropdown 'Draft' selected and Search applied filters visible rows", () => {
    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    // Select "Draft" from dropdown
    const statusSelect = screen.getByLabelText("Filter by status");
    fireEvent.change(statusSelect, { target: { value: "draft" } });

    // Click Search button to apply filter
    const searchBtn = screen.getByTestId("quotes-search-btn");
    fireEvent.click(searchBtn);

    // Mock returns filtered results for "draft"
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
    expect(screen.queryByText("Johnson Services")).toBeNull();
  });

  it("tech role — RoleGate blocks ALL quotes content (absent from DOM)", () => {
    const { container } = render(<QuotesPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(container.textContent).toBe("");
    expect(screen.queryByText("Smith Electrical")).toBeNull();
  });

  it("office_staff can see quotes", () => {
    render(<QuotesPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="office_staff">{children}</Wrapper>
      ),
    });
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
  });

  it("row links navigate to /quotes/[id]", () => {
    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    const links = screen.getAllByRole("link");
    const firstLink = links[0];
    expect(firstLink?.getAttribute("href")).toContain("/quotes/");
  });

  it("empty state when API returns empty array", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: { items: [], total: 0, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText(/no quotes yet/i)).toBeTruthy();
  });

  it("error state when API returns error", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as never);

    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText(/could not load quotes/i)).toBeTruthy();
  });
});
