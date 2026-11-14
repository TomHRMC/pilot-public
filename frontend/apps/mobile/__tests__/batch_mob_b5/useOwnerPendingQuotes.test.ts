/**
 * useOwnerPendingQuotes unit tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/useOwnerPendingQuotes.test.ts
 *
 * Verifies:
 *   - Calls GET /api/v1/quotes with status=pending_approval param
 *   - Does NOT include submitted_by param
 *   - Returns pendingCount = array.length
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { MOCK_PENDING_QUOTES } from "../../mocks/handlers/ownerHandlers";
import { useOwnerPendingQuotes } from "../../features/owner-tab/hooks/useOwnerPendingQuotes";

// ── Mocks ──────────────────────────────────────────────────────────────────────

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
  }),
}));

// ── Server ─────────────────────────────────────────────────────────────────────

let capturedUrl: string | null = null;

// Backend returns PaginatedQuoteListResponse { items, total, limit, offset }
const server = setupServer(
  http.get("*/api/v1/quotes", ({ request }) => {
    capturedUrl = request.url;
    return HttpResponse.json({
      items: MOCK_PENDING_QUOTES,
      total: MOCK_PENDING_QUOTES.length,
      limit: 100,
      offset: 0,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedUrl = null;
});
afterAll(() => server.close());

// ── Wrapper ────────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("useOwnerPendingQuotes", () => {
  it("calls GET /api/v1/quotes with status=pending_approval param", async () => {
    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(capturedUrl).not.toBeNull();
    const url = new URL(capturedUrl!);
    expect(url.searchParams.get("status")).toBe("pending_approval");
  });

  it("does NOT include submitted_by param in the request", async () => {
    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(capturedUrl).not.toBeNull();
    const url = new URL(capturedUrl!);
    expect(url.searchParams.get("submitted_by")).toBeNull();
  });

  it("includes limit=100 param in the request", async () => {
    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(capturedUrl).not.toBeNull();
    const url = new URL(capturedUrl!);
    expect(url.searchParams.get("limit")).toBe("100");
  });

  it("returns pendingCount equal to the array length from the response", async () => {
    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.pendingCount).toBe(MOCK_PENDING_QUOTES.length);
    expect(result.current.pendingCount).toBe(2);
  });

  it("returns quotes array from response", async () => {
    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.quotes).toHaveLength(2);
    expect(result.current.quotes[0].status_code).toBe("pending_approval");
  });

  it("returns pendingCount=0 and empty quotes when API returns empty array", async () => {
    server.use(
      http.get("*/api/v1/quotes", () =>
        HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
      ),
    );

    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.pendingCount).toBe(0);
    expect(result.current.quotes).toHaveLength(0);
  });

  it("sets isError=true when API returns 500", async () => {
    server.use(
      http.get("*/api/v1/quotes", () =>
        HttpResponse.json({ detail: "error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useOwnerPendingQuotes(), { wrapper });

    // Wait for isError directly — hook has retry:1 which may delay isLoading→false
    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 5000,
    });

    expect(result.current.isError).toBe(true);
  });
});
