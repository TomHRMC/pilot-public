/**
 * ApprovalsQueueSection unit tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/ApprovalsQueueSection.test.tsx
 *
 * Verifies:
 *   - pendingCount>0 → "N quotes awaiting approval" visible
 *   - pendingCount=0 → "All caught up" visible
 *   - Press → router.push called with (home)/quotes/pending
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { MOCK_PENDING_QUOTES } from "../../mocks/handlers/ownerHandlers";
import { ApprovalsQueueSection } from "../../features/owner-tab/components/ApprovalsQueueSection";

// ── Mocks ──────────────────────────────────────────────────────────────────────

const mockRouterPush = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "owner-001", role: "owner", tenantId: "tenant-001" },
    isAuthenticated: true,
    role: "owner",
  }),
}));

// ── Server ─────────────────────────────────────────────────────────────────────

// Backend returns PaginatedQuoteListResponse { items, total, limit, offset }
const server = setupServer(
  http.get("*/api/v1/quotes", () =>
    HttpResponse.json({
      items: MOCK_PENDING_QUOTES,
      total: MOCK_PENDING_QUOTES.length,
      limit: 100,
      offset: 0,
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  mockRouterPush.mockClear();
});
afterAll(() => server.close());

// ── Wrapper ────────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("ApprovalsQueueSection", () => {
  it("renders '2 quotes awaiting approval' when pendingCount=2", async () => {
    render(<ApprovalsQueueSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("2 quotes awaiting approval")).toBeTruthy();
    });
  });

  it("renders badge with count when pendingCount>0", async () => {
    render(<ApprovalsQueueSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("approvals-badge")).toBeTruthy();
      expect(screen.getByText("2")).toBeTruthy();
    });
  });

  it("renders 'All caught up ✓' when pendingCount=0", async () => {
    server.use(
      http.get("*/api/v1/quotes", () =>
        HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
      ),
    );

    render(<ApprovalsQueueSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("All caught up ✓")).toBeTruthy();
    });
  });

  it("does NOT render badge when pendingCount=0", async () => {
    server.use(
      http.get("*/api/v1/quotes", () =>
        HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
      ),
    );

    render(<ApprovalsQueueSection />, { wrapper });

    await waitFor(() => {
      expect(screen.queryByTestId("approvals-badge")).toBeNull();
    });
  });

  it("press calls router.push with (home)/quotes/pending", async () => {
    render(<ApprovalsQueueSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("approvals-queue-section")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("approvals-queue-section"));

    expect(mockRouterPush).toHaveBeenCalledWith(
      "/(tabs)/(home)/quotes/pending",
    );
  });

  it("returns null when hook isError=true (fails silently)", async () => {
    server.use(
      http.get("*/api/v1/quotes", () =>
        HttpResponse.json({ detail: "error" }, { status: 500 }),
      ),
    );

    const { toJSON } = render(<ApprovalsQueueSection />, { wrapper });

    // Hook has retry:1 — wait longer for retry+failure cycle to complete
    await waitFor(
      () => {
        expect(toJSON()).toBeNull();
      },
      { timeout: 5000 },
    );
  });
});
