/**
 * Owner tab integration tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/owner-tab.integration.test.tsx
 *
 * Tests OwnerTab full screen with MSW-intercepted API calls.
 * Verifies:
 *   - Placeholder "coming in FE-B3+" removed
 *   - All new section testIDs rendered
 *   - Sign-out button visible and functional
 *   - QB connected/disconnected states
 *   - AR summary with counts
 *   - Approvals queue with count
 *   - Plan tier name rendered
 */

import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  MOCK_PENDING_QUOTES,
  MOCK_QB_CONNECTED,
  MOCK_QB_DISCONNECTED,
  MOCK_INVOICES,
  MOCK_SUBSCRIPTION,
} from "../../mocks/handlers/ownerHandlers";
import OwnerTab from "../../app/(tabs)/owner";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockRouterReplace = jest.fn();
const mockRouterPush = jest.fn();
const mockSignOut = jest.fn().mockResolvedValue(undefined);

jest.mock("expo-router", () => ({
  useRouter: () => ({
    replace: mockRouterReplace,
    push: mockRouterPush,
  }),
  router: { push: mockRouterPush },
}));

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: {
      id: "owner-user-001",
      email: "owner@test.com",
      role: "owner",
      tenantId: "tenant-001",
      displayName: "Test Owner",
      accessToken: "token",
    },
    isAuthenticated: true,
    role: "owner",
    signOut: mockSignOut,
  }),
}));

jest.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ── Server ─────────────────────────────────────────────────────────────────────

// Backend returns PaginatedQuoteListResponse { items, total, limit, offset }
const server = setupServer(
  http.get("*/api/v1/quotes", ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get("status") === "pending_approval") {
      return HttpResponse.json({
        items: MOCK_PENDING_QUOTES,
        total: MOCK_PENDING_QUOTES.length,
        limit: 100,
        offset: 0,
      });
    }
    return HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 });
  }),
  http.get("*/api/v1/integrations/quickbooks/status", () =>
    HttpResponse.json(MOCK_QB_CONNECTED),
  ),
  http.get("*/api/v1/invoices/", () => HttpResponse.json(MOCK_INVOICES)),
  http.get("*/api/v1/tenants/:tenantId/subscription", () =>
    HttpResponse.json(MOCK_SUBSCRIPTION),
  ),
  // Calendar status (existing section)
  http.get("*/api/v1/integrations/calendar/status", () =>
    HttpResponse.json({
      is_connected: true,
      provider_code: "google",
      sync_status: "synced",
      connection_status: "active",
      connected_at: "2026-05-01T00:00:00Z",
      token_expires_at: null,
      last_sync_at: null,
      last_successful_sync_at: null,
      pending_conflicts_count: 0,
      requires_reconnect: false,
    }),
  ),
  // Field issues status (existing section)
  http.get("*/api/v1/jobs/field-issues/", () =>
    HttpResponse.json({ pending_count: 0 }),
  ),
);

let qc: QueryClient;

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
  mockRouterReplace.mockClear();
  mockRouterPush.mockClear();
  mockSignOut.mockClear();
});
afterAll(() => server.close());

// ── Wrapper ────────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  qc = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("OwnerTab integration (MOB-B5)", () => {
  it("does NOT render the placeholder text 'coming in FE-B3+'", () => {
    render(<OwnerTab />, { wrapper });

    expect(screen.queryByText(/coming in FE-B3\+/i)).toBeNull();
  });

  it("renders ApprovalsQueueSection with pending count", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("approvals-queue-section")).toBeTruthy();
    });

    expect(screen.getByText("2 quotes awaiting approval")).toBeTruthy();
  });

  it("renders QbSyncStatusSection with 'Connected' state", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("qb-sync-status-section")).toBeTruthy();
    });

    expect(screen.getByText("Connected · Acme Electrical LLC")).toBeTruthy();
  });

  it("renders QbSyncStatusSection with 'Not connected' state when disconnected", async () => {
    server.use(
      http.get("*/api/v1/integrations/quickbooks/status", () =>
        HttpResponse.json(MOCK_QB_DISCONNECTED),
      ),
    );

    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Not connected — Connect →")).toBeTruthy();
    });
  });

  it("renders ArSummarySection with 3 outstanding invoices", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("ar-summary-section")).toBeTruthy();
    });

    expect(screen.getByText("3 outstanding")).toBeTruthy();
  });

  it("renders PlanUsageSection with tier name", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("plan-usage-section")).toBeTruthy();
    });

    expect(screen.getByText("Starter Plan")).toBeTruthy();
  });

  it("renders sign-out button", () => {
    render(<OwnerTab />, { wrapper });

    expect(screen.getByTestId("signout-button")).toBeTruthy();
    expect(screen.getByText("Sign out")).toBeTruthy();
  });

  it("sign-out calls signOut() and redirects to /(auth)/login", async () => {
    render(<OwnerTab />, { wrapper });

    fireEvent.press(screen.getByTestId("signout-button"));

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalled();
    });

    expect(mockRouterReplace).toHaveBeenCalledWith("/(auth)/login");
  });

  it("renders 'Owner' screen title", () => {
    render(<OwnerTab />, { wrapper });

    expect(screen.getByText("Owner")).toBeTruthy();
  });

  it("renders testID owner-tab-screen (SafeAreaView wrapper)", () => {
    render(<OwnerTab />, { wrapper });

    expect(screen.getByTestId("owner-tab-screen")).toBeTruthy();
  });

  it("tapping approvals section navigates to (home)/quotes/pending", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("approvals-queue-section")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("approvals-queue-section"));

    expect(mockRouterPush).toHaveBeenCalledWith(
      "/(tabs)/(home)/quotes/pending",
    );
  });

  it("renders AR overdue badge when 1 invoice is overdue", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("ar-overdue-badge")).toBeTruthy();
    });

    expect(screen.getByText("1 overdue")).toBeTruthy();
  });

  it("plan section shows user count from usage", async () => {
    render(<OwnerTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("plan-usage-section")).toBeTruthy();
    });

    // MOCK_SUBSCRIPTION has current_user_count=3, max_users=5
    expect(screen.getByText("3/5 users")).toBeTruthy();
  });
});
