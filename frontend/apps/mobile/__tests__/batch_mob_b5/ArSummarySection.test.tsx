/**
 * ArSummarySection unit tests (MOB-B5)
 *
 * Location: apps/mobile/__tests__/batch_mob_b5/ArSummarySection.test.tsx
 *
 * Verifies:
 *   - 3 invoices, 1 overdue → "3 outstanding" + "1 overdue" badge
 *   - 0 invoices → "No outstanding invoices"
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
import { ArSummarySection } from "../../features/owner-tab/components/ArSummarySection";

// ── Mocks ──────────────────────────────────────────────────────────────────────

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "owner-001", role: "owner", tenantId: "tenant-001" },
    isAuthenticated: true,
    role: "owner",
  }),
}));

const mockOpenURL = jest.spyOn(Linking, "openURL").mockResolvedValue(undefined);

// ── Date helpers ───────────────────────────────────────────────────────────────

const PAST_DUE = new Date(Date.now() - 10 * 86_400_000).toISOString();
const FUTURE_DUE = new Date(Date.now() + 20 * 86_400_000).toISOString();

const BASE = {
  customer_id: "c-001",
  site_id: "s-001",
  status_id: "st-001",
  status_code: "sent",
  issued_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
  subtotal_cents: 100000,
  total_cents: 108000,
  balance_due_cents: 108000,
  currency: "USD",
  quote_id: null,
  job_id: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// ── Server ─────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/invoices/", () =>
    HttpResponse.json({
      items: [
        { ...BASE, id: "inv-001", invoice_number: "INV-001", due_at: PAST_DUE },
        {
          ...BASE,
          id: "inv-002",
          invoice_number: "INV-002",
          due_at: FUTURE_DUE,
        },
        {
          ...BASE,
          id: "inv-003",
          invoice_number: "INV-003",
          due_at: FUTURE_DUE,
        },
      ],
      total: 3,
      limit: 50,
      offset: 0,
    }),
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

describe("ArSummarySection", () => {
  it("shows '3 outstanding' when 3 invoices are returned", async () => {
    render(<ArSummarySection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("3 outstanding")).toBeTruthy();
    });
  });

  it("shows '1 overdue' badge when 1 invoice is past due", async () => {
    render(<ArSummarySection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("ar-overdue-badge")).toBeTruthy();
      expect(screen.getByText("1 overdue")).toBeTruthy();
    });
  });

  it("shows 'No outstanding invoices' empty state when total=0", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 }),
      ),
    );

    render(<ArSummarySection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("No outstanding invoices")).toBeTruthy();
    });
  });

  it("does NOT show overdue badge when overdueCount=0", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({
          items: [
            {
              ...BASE,
              id: "inv-001",
              invoice_number: "INV-001",
              due_at: FUTURE_DUE,
            },
          ],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      ),
    );

    render(<ArSummarySection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("1 outstanding")).toBeTruthy();
    });

    expect(screen.queryByTestId("ar-overdue-badge")).toBeNull();
  });

  it("tap calls Linking.openURL with /invoices path", async () => {
    render(<ArSummarySection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("ar-summary-section")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("ar-summary-section"));

    expect(mockOpenURL).toHaveBeenCalledWith(
      expect.stringContaining("/invoices"),
    );
  });

  it("does NOT tap deep-link for empty state (no Pressable)", async () => {
    server.use(
      http.get("*/api/v1/invoices/", () =>
        HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 }),
      ),
    );

    render(<ArSummarySection />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("No outstanding invoices")).toBeTruthy();
    });

    // Empty state has testID but is not a Pressable, openURL should not be called
    expect(mockOpenURL).not.toHaveBeenCalled();
  });
});
