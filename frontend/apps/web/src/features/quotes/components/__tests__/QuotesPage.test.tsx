/**
 * QuotesPage unit tests — UI-FIX-1C update
 *
 * Location: apps/web/src/features/quotes/components/__tests__/QuotesPage.test.tsx
 *
 * UI-FIX-1C: useQuotes now returns PaginatedResult<QuoteListItem>.
 * Mock updated to return { items, total, limit, offset } shape.
 * Status filter pills replaced with <select> dropdown — tests updated.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { QuotesPage } from "../QuotesPage";

// Mock next/navigation — QuotesPage uses useRouter for the "New Quote" button
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/quotes",
  useRouter: () => ({ push: mockPush }),
}));

// Mock useConvertQuote — prevent real mutation in unit tests
vi.mock("../../hooks/useConvertQuote", () => ({
  useConvertQuote: () => ({ mutate: vi.fn(), isPending: false }),
}));

// Mock useQuotes hook — UI-FIX-1C: returns paginated shape
vi.mock("../../hooks/useQuotes", () => ({
  useQuotes: vi.fn(),
  QUOTES_QUERY_KEY: (options: Record<string, unknown>) => ["quotes", options],
}));

import { useQuotes } from "../../hooks/useQuotes";

const MOCK_QUOTES = [
  {
    id: "q-00000001",
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
    id: "q-00000002",
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
const MOCK_PAGINATED = {
  items: MOCK_QUOTES,
  total: 2,
  limit: 25,
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
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("QuotesPage", () => {
  beforeEach(() => {
    vi.mocked(useQuotes).mockReset();
  });

  it("renders loading state for owner", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getAllByText(/loading quotes/i).length).toBeGreaterThan(0);
  });

  it("renders quote list with paginated mock data for owner", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
    expect(screen.getByText("Johnson Services")).toBeTruthy();
  });

  it("status filter dropdown exists and passes server-side status param to useQuotes (UI-FIX-1C)", () => {
    // UI-FIX-1C: Filter is now a <select> dropdown — user picks status then clicks Search
    vi.mocked(useQuotes).mockImplementation(({ status } = {}) => {
      const items = status
        ? MOCK_QUOTES.filter((q) => q.status_code === status)
        : MOCK_QUOTES;
      return {
        data: { items, total: items.length, limit: 25, offset: 0 },
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      } as never;
    });

    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    // Before filter — both visible
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
    expect(screen.getByText("Johnson Services")).toBeTruthy();

    // Status dropdown exists (not pills)
    const statusSelect = screen.getByLabelText("Filter by status");
    expect(statusSelect).toBeTruthy();

    // Change select to "Draft"
    fireEvent.change(statusSelect, { target: { value: "draft" } });

    // Click Search to apply filter
    const searchBtn = screen.getByTestId("quotes-search-btn");
    fireEvent.click(searchBtn);

    // After filter — only draft quote visible (mock filters by status param)
    expect(screen.getByText("Smith Electrical")).toBeTruthy();
    expect(screen.queryByText("Johnson Services")).toBeNull();
  });

  it("tech role does NOT see quotes content (RoleGate blocks)", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    const { container } = render(<QuotesPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });
    expect(container.textContent).toBe("");
    expect(screen.queryByText("Smith Electrical")).toBeNull();
  });

  it("renders empty state when no quotes", () => {
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

  it("quote ID is a link to /quotes/[id]", () => {
    vi.mocked(useQuotes).mockReturnValue({
      data: MOCK_PAGINATED,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as never);

    render(<QuotesPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    const links = screen.getAllByRole("link");
    const firstLink = links[0];
    expect(firstLink?.getAttribute("href")).toContain("/quotes/");
  });
});
