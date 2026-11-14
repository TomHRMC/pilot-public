/**
 * Unit tests — useRecentComms hook
 *
 * Location: apps/web/src/features/comms/hooks/__tests__/useRecentComms.test.tsx
 *
 * Tests:
 * 1. Returns data with the mock response shape
 * 2. Enters error state on 500
 * 3. Query key includes all filter params
 * 4. Query key normalizes undefined params to empty strings
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useRecentComms,
  RECENT_COMMS_QUERY_KEY,
  COMMS_PAGE_SIZE,
} from "../useRecentComms";

// ── MSW ───────────────────────────────────────────────────────────────────────

const MOCK_ITEM = {
  id: "comm-test-001",
  customer_id: "customer-001",
  customer_name: "John Smith",
  channel: "sms",
  direction: "outbound",
  body: "Hi! I'm on my way.",
  created_at: "2026-07-28T12:00:00.000Z",
};

const MOCK_RESPONSE = {
  items: [MOCK_ITEM],
  total: 1,
  limit: 50,
  offset: 0,
};

const server = setupServer(
  http.get("/api/v1/communications/recent", () =>
    HttpResponse.json(MOCK_RESPONSE),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test wrapper (retry: false per Rule 14) ──────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useRecentComms", () => {
  it("1. returns data with the mock response shape", async () => {
    const { result } = renderHook(
      () => useRecentComms({ limit: COMMS_PAGE_SIZE, offset: 0 }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_RESPONSE);
    expect(result.current.data?.items[0]).toEqual(MOCK_ITEM);
  });

  it("2. enters error state on 500", async () => {
    server.use(
      http.get("/api/v1/communications/recent", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(
      () => useRecentComms({ limit: COMMS_PAGE_SIZE, offset: 0 }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });

  it("3. query key includes all filter params", () => {
    const params = {
      limit: 50,
      offset: 10,
      customer_search: "John",
      channel: "sms",
      sent_from: "2026-07-01",
      sent_to: "2026-07-28",
    };
    const key = RECENT_COMMS_QUERY_KEY(params);
    expect(key[0]).toBe("recent-comms");
    expect(key[1]).toEqual({
      limit: 50,
      offset: 10,
      customer_search: "John",
      channel: "sms",
      sent_from: "2026-07-01",
      sent_to: "2026-07-28",
    });
  });

  it("4. query key normalizes undefined params to empty strings", () => {
    const key = RECENT_COMMS_QUERY_KEY({
      limit: 50,
      offset: 0,
    });
    expect(key[1]).toEqual({
      limit: 50,
      offset: 0,
      customer_search: "",
      channel: "",
      sent_from: "",
      sent_to: "",
    });
  });
});
