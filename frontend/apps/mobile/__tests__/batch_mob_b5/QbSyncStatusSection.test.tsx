/**
 * QbSyncStatusSection unit tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/QbSyncStatusSection.test.tsx
 *
 * Verifies:
 *   - is_connected=true, connection_status="active" → "Connected" visible
 *   - is_connected=false → "Not connected — Connect →" visible
 *   - Connect link press → Linking.openURL called with QB settings URL
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
import { Linking } from "react-native";
import {
  MOCK_QB_CONNECTED,
  MOCK_QB_DISCONNECTED,
} from "../../mocks/handlers/ownerHandlers";
import { QbSyncStatusSection } from "../../features/owner-tab/components/QbSyncStatusSection";

// ── Mocks ──────────────────────────────────────────────────────────────────────

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "owner-001", role: "owner", tenantId: "tenant-001" },
    isAuthenticated: true,
    role: "owner",
  }),
}));

const mockOpenURL = jest.spyOn(Linking, "openURL").mockResolvedValue(undefined);

// ── Server ─────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/integrations/quickbooks/status", () =>
    HttpResponse.json(MOCK_QB_CONNECTED),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  mockOpenURL.mockClear();
});
afterAll(() => server.close());

// ── Wrapper ────────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("QbSyncStatusSection", () => {
  it("shows 'Connected' when is_connected=true and connection_status=active", async () => {
    render(<QbSyncStatusSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Connected · Acme Electrical LLC")).toBeTruthy();
    });
  });

  it("shows company name in connected state", async () => {
    render(<QbSyncStatusSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Connected · Acme Electrical LLC")).toBeTruthy();
    });
  });

  it("shows 'Not connected — Connect →' when is_connected=false", async () => {
    server.use(
      http.get("*/api/v1/integrations/quickbooks/status", () =>
        HttpResponse.json(MOCK_QB_DISCONNECTED),
      ),
    );

    render(<QbSyncStatusSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Not connected — Connect →")).toBeTruthy();
    });
  });

  it("shows 'Not connected — Connect →' when connection_status is not active", async () => {
    server.use(
      http.get("*/api/v1/integrations/quickbooks/status", () =>
        HttpResponse.json({
          ...MOCK_QB_CONNECTED,
          is_connected: true,
          connection_status: "expired",
        }),
      ),
    );

    render(<QbSyncStatusSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Not connected — Connect →")).toBeTruthy();
    });
  });

  it("connect link press calls Linking.openURL with QB settings URL", async () => {
    server.use(
      http.get("*/api/v1/integrations/quickbooks/status", () =>
        HttpResponse.json(MOCK_QB_DISCONNECTED),
      ),
    );

    render(<QbSyncStatusSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("qb-connect-link")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("qb-connect-link"));

    expect(mockOpenURL).toHaveBeenCalledWith(
      expect.stringContaining("/settings/integrations/quickbooks"),
    );
  });

  it("does NOT display last_sync_at (not in API response)", async () => {
    render(<QbSyncStatusSection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("qb-sync-status-section")).toBeTruthy();
    });

    // Verify no last sync text is rendered
    expect(screen.queryByText(/last sync/i)).toBeNull();
    expect(screen.queryByText(/synced at/i)).toBeNull();
  });
});
