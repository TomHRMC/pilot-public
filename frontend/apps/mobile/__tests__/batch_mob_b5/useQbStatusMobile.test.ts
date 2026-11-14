/**
 * useQbStatusMobile unit tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/useQbStatusMobile.test.ts
 *
 * Verifies:
 *   - Calls GET /api/v1/integrations/quickbooks/status
 *   - Returns connected fixture data correctly
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  MOCK_QB_CONNECTED,
  MOCK_QB_DISCONNECTED,
} from "../../mocks/handlers/ownerHandlers";
import { useQbStatusMobile } from "../../features/owner-tab/hooks/useQbStatusMobile";

// ── Mocks ──────────────────────────────────────────────────────────────────────

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "owner-001", role: "owner", tenantId: "tenant-001" },
    isAuthenticated: true,
    role: "owner",
  }),
}));

// ── Server ─────────────────────────────────────────────────────────────────────

let capturedUrl: string | null = null;

const server = setupServer(
  http.get("*/api/v1/integrations/quickbooks/status", ({ request }) => {
    capturedUrl = request.url;
    return HttpResponse.json(MOCK_QB_CONNECTED);
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

describe("useQbStatusMobile", () => {
  it("calls GET /api/v1/integrations/quickbooks/status", async () => {
    const { result } = renderHook(() => useQbStatusMobile(), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(capturedUrl).not.toBeNull();
    expect(capturedUrl).toContain("/api/v1/integrations/quickbooks/status");
  });

  it("returns connected fixture data when API returns connected state", async () => {
    const { result } = renderHook(() => useQbStatusMobile(), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.is_connected).toBe(true);
    expect(result.current.data?.connection_status).toBe("active");
    expect(result.current.data?.company_name).toBe("Acme Electrical LLC");
  });

  it("returns disconnected data when API returns not_configured state", async () => {
    server.use(
      http.get("*/api/v1/integrations/quickbooks/status", () =>
        HttpResponse.json(MOCK_QB_DISCONNECTED),
      ),
    );

    const { result } = renderHook(() => useQbStatusMobile(), { wrapper });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.is_connected).toBe(false);
    expect(result.current.data?.connection_status).toBe("not_configured");
    expect(result.current.data?.company_name).toBeNull();
  });

  it("sets isError=true when API returns 500 (after retry cycle)", async () => {
    server.use(
      http.get("*/api/v1/integrations/quickbooks/status", () =>
        HttpResponse.json({ detail: "error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useQbStatusMobile(), { wrapper });

    // The hook has retry:1 — QueryClient defaultOptions.retry:false (retry:0) is
    // overridden at hook level. Wait up to 10s for the retry cycle to complete.
    await waitFor(
      () => {
        expect(result.current.isError).toBe(true);
      },
      { timeout: 10_000 },
    );
  });
});
