/**
 * COMMS-UI-B1 Integration — Communications Page: TanStack Table + Search + Filter + Paginator
 *
 * Location: apps/web/src/__tests__/batch_comms_ui_b1/comms_ui_b1.integration.test.tsx
 *
 * Tests:
 * 1. Route renders (comms-page + recent-comms-table present with MSW data)
 * 2. RoleGate — tech role without comms.send sees nothing
 * 3. Customer search input fires request with customer_search
 * 4. Channel pill Email → shows email rows only; SMS → shows SMS rows only
 * 5. Sorting a column reorders rows
 * 6. PilotPaginator next-page click calls API with increased offset
 * 7. Empty state string renders when handler returns no items
 *
 * RULE: Uses MSW (never real backend). Asserts by specific content/IDs.
 * RULE: retry: false on QueryClient (Rule 14).
 * RULE: server.resetHandlers() in afterEach (Rule 15).
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
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser, PilotRole } from "@pilot/ui/auth";
import { CommsPage } from "@/features/comms/components/CommsPage";
import { communicationHandlers } from "@/mocks/handlers/communications";

// ── Mock permissions: remove comms.send from technician to prove RoleGate ────
//
// All seeded roles currently HAVE comms.send. We mock the permissions module
// to remove it from technician, then render with role="technician" to prove the gate
// hides content for unauthorized roles.
vi.mock("@pilot/ui/role-gate/permissions", async (importOriginal) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const actual: any = await importOriginal();
  const techPerms = new Set(actual.ROLE_PERMISSION_MAP.technician);
  techPerms.delete("comms.send");
  return {
    ...actual,
    ROLE_PERMISSION_MAP: {
      ...actual.ROLE_PERMISSION_MAP,
      technician: techPerms,
    },
  };
});

// ── Navigation + Link mocks ──────────────────────────────────────────────────

const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  usePathname: () => "/comms",
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

const server = setupServer(...communicationHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(role: PilotRole = "owner"): AuthContextValue {
  const user: PilotUser = {
    id: "u-comms-ui-b1",
    email: "test@pilot.example.com",
    role,
    tenantId: "t-comms-ui-b1",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper(role: PilotRole = "owner") {
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

describe("COMMS-UI-B1 — Communications Page", () => {
  // 1. Route renders with MSW data
  it("1. renders comms-page and recent-comms-table with MSW data", async () => {
    render(<CommsPage />, { wrapper: createWrapper("owner") });

    await waitFor(() => {
      expect(screen.getByTestId("comms-page")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId("recent-comms-table")).toBeInTheDocument();
    });

    // Assert a specific customer name from the fixture is visible
    expect(screen.getAllByText("John Smith").length).toBeGreaterThan(0);
  });

  // 2. RoleGate — tech role (without comms.send) sees nothing
  it("2. tech role without comms.send sees nothing", () => {
    render(<CommsPage />, { wrapper: createWrapper("technician") });

    expect(screen.queryByTestId("comms-page")).not.toBeInTheDocument();
  });

  // 3. Customer search input fires request with customer_search
  it("3. customer search filters rows by name", async () => {
    render(<CommsPage />, { wrapper: createWrapper("owner") });

    await waitFor(() => {
      expect(screen.getByTestId("recent-comms-table")).toBeInTheDocument();
    });

    // Type in the search input
    const searchInput = screen.getByTestId("comms-customer-search");
    fireEvent.change(searchInput, { target: { value: "Sarah" } });

    // Wait for debounce (300ms) + refetch — both conditions must be true:
    // Sarah Connor visible AND John Smith NOT visible (only after refetch)
    await waitFor(
      () => {
        expect(screen.getAllByText("Sarah Connor").length).toBeGreaterThan(0);
        const table = screen.getByTestId("recent-comms-table");
        expect(within(table).queryByText("John Smith")).not.toBeInTheDocument();
      },
      { timeout: 5000 },
    );
  });

  // 4. Channel pill Email → shows email rows only; SMS → shows SMS rows only
  it("4. channel Email pill shows only email rows; SMS shows only SMS rows", async () => {
    render(<CommsPage />, { wrapper: createWrapper("owner") });

    await waitFor(() => {
      expect(screen.getByTestId("recent-comms-table")).toBeInTheDocument();
    });

    // Click the Email pill — fixture: comm-100 is email, comm-101 is sms
    const emailPill = screen.getByRole("button", { name: "Email" });
    fireEvent.click(emailPill);

    // Wait for refetch — comm-100 (email) present, comm-101 (sms) absent
    await waitFor(
      () => {
        expect(screen.getByTestId("comm-row-comm-100")).toBeInTheDocument();
        expect(
          screen.queryByTestId("comm-row-comm-101"),
        ).not.toBeInTheDocument();
      },
      { timeout: 5000 },
    );

    // Click the SMS pill — comm-101 (sms) present, comm-100 (email) absent
    const smsPill = screen.getByRole("button", { name: "SMS" });
    fireEvent.click(smsPill);

    await waitFor(
      () => {
        expect(screen.getByTestId("comm-row-comm-101")).toBeInTheDocument();
        expect(
          screen.queryByTestId("comm-row-comm-100"),
        ).not.toBeInTheDocument();
      },
      { timeout: 5000 },
    );
  });

  // 5. Sorting a column reorders rows
  it("5. sorting by Customer reorders rows alphabetically", async () => {
    render(<CommsPage />, { wrapper: createWrapper("owner") });

    await waitFor(() => {
      expect(screen.getByTestId("recent-comms-table")).toBeInTheDocument();
    });

    // Click the Customer column header to sort ascending
    const tableEl = screen.getByTestId("recent-comms-table");
    const customerHeaderCell = within(tableEl)
      .getByText("Customer")
      .closest("th");
    fireEvent.click(customerHeaderCell!);

    // After sorting ascending, the first row should be "Bob Davis"
    // (alphabetically first among the fixture customers)
    await waitFor(() => {
      const rows = screen.getAllByTestId(/^comm-row-/);
      expect(rows.length).toBeGreaterThan(0);
      expect(within(rows[0]).getByText("Bob Davis")).toBeInTheDocument();
    });
  });

  // 6. PilotPaginator next-page click calls API with increased offset
  it("6. paginator next-page shows page 2 rows", async () => {
    render(<CommsPage />, { wrapper: createWrapper("owner") });

    await waitFor(() => {
      expect(screen.getByTestId("recent-comms-table")).toBeInTheDocument();
    });

    // Page 1: comm-100 to comm-149 (50 items, limit=50)
    // comm-150 is on page 2 (offset=50)
    expect(screen.queryByTestId("comm-row-comm-150")).not.toBeInTheDocument();

    // Click next-page button
    const nextButton = screen.getByRole("button", { name: "Next page" });
    fireEvent.click(nextButton);

    // Page 2: comm-150 to comm-154 (5 items)
    await waitFor(
      () => {
        expect(screen.getByTestId("comm-row-comm-150")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  // 7. Empty state string renders when handler returns no items
  it("7. shows empty state string when handler returns no items", async () => {
    server.use(
      http.get("/api/v1/communications/recent", () =>
        HttpResponse.json({
          items: [],
          total: 0,
          limit: 50,
          offset: 0,
        }),
      ),
    );

    render(<CommsPage />, { wrapper: createWrapper("owner") });

    await waitFor(() => {
      expect(
        screen.getByText(
          "No messages sent yet. Visit a customer to send their first message.",
        ),
      ).toBeInTheDocument();
    });
  });
});
