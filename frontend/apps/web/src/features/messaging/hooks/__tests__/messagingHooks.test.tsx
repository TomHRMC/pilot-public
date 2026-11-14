/**
 * C-B9 Unit Tests — Messaging Hooks
 *
 * Location: apps/web/src/features/messaging/hooks/__tests__/messagingHooks.test.tsx
 *
 * Tests each hook: returns data in expected shape, returns error state,
 * correct query key.
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
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
} from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

import {
  useProvisioningStatus,
  PROVISIONING_STATUS_QUERY_KEY,
} from "../useProvisioningStatus";
import {
  useCarrierVerticals,
  CARRIER_VERTICALS_QUERY_KEY,
} from "../useCarrierVerticals";
import { useAvailablePhoneNumbers } from "../useAvailablePhoneNumbers";
import { useCarrierQuote, CARRIER_QUOTE_QUERY_KEY } from "../useCarrierQuote";

// ── MSW ───────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
    HttpResponse.json({
      registration_id: "reg-001",
      status: "quoting",
      entity_type: "standard",
      telnyx_brand_id: null,
      telnyx_campaign_id: null,
      telnyx_phone_number: null,
      quoted_setup_cents: 400000,
      quoted_monthly_cents: 30000,
      otp_requested_at: null,
      failure_reason: null,
      updated_at: "2026-08-06T12:00:00Z",
    }),
  ),
  http.get("/api/v1/tenants/:tenantId/messaging/verticals", () =>
    HttpResponse.json({ verticals: ["ELECTRICIAN", "CONTRACTOR"] }),
  ),
  http.get("/api/v1/tenants/:tenantId/messaging/available-numbers", () =>
    HttpResponse.json({
      numbers: [
        {
          phone_number: "+13025551234",
          locality: "Wilmington",
          region: "DE",
          monthly_cost_millicents: 100000,
        },
      ],
    }),
  ),
  http.get("/api/v1/tenants/:tenantId/messaging/quote", () =>
    HttpResponse.json({
      entity_type: "standard",
      setup_total_millicents: 400000,
      recurring_monthly_millicents: 30000,
      setup_items: [],
      recurring_items: [],
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-test",
      email: "test@pilot.example.com",
      role: "owner",
      tenantId: "t-test",
      displayName: "Test",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuth()}>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  return Wrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useProvisioningStatus", () => {
  it("returns data in expected shape", async () => {
    const { result } = renderHook(() => useProvisioningStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).not.toBeNull();
    expect(result.current.data!.status).toBe("quoting");
    expect(result.current.data!.entity_type).toBe("standard");
    expect(result.current.data!.registration_id).toBe("reg-001");
  });

  it("returns null on 404 (not started)", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );

    const { result } = renderHook(() => useProvisioningStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("uses correct query key", () => {
    expect(PROVISIONING_STATUS_QUERY_KEY).toEqual(["messaging", "status"]);
  });
});

describe("useCarrierVerticals", () => {
  it("returns verticals array", async () => {
    const { result } = renderHook(() => useCarrierVerticals(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data!.verticals).toContain("ELECTRICIAN");
    expect(result.current.data!.verticals).toContain("CONTRACTOR");
  });

  it("uses correct query key", () => {
    expect(CARRIER_VERTICALS_QUERY_KEY).toEqual(["messaging", "verticals"]);
  });
});

describe("useAvailablePhoneNumbers", () => {
  it("returns numbers when area code provided", async () => {
    const { result } = renderHook(() => useAvailablePhoneNumbers("302"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data!.numbers).toHaveLength(1);
    expect(result.current.data!.numbers[0].phone_number).toBe("+13025551234");
  });

  it("is disabled when area code is null", () => {
    const { result } = renderHook(() => useAvailablePhoneNumbers(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.isEnabled).toBe(false);
  });
});

describe("useCarrierQuote", () => {
  it("returns quote data in expected shape", async () => {
    const { result } = renderHook(() => useCarrierQuote(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data!.entity_type).toBe("standard");
    expect(result.current.data!.setup_total_millicents).toBe(400000);
    expect(result.current.data!.recurring_monthly_millicents).toBe(30000);
  });

  it("uses correct query key", () => {
    expect(CARRIER_QUOTE_QUERY_KEY).toEqual(["messaging", "quote"]);
  });
});
