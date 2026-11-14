/**
 * FE-B24 — Quote Metadata Edit Modal Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b24/quote_metadata_edit.integration.test.tsx
 *
 * Tests:
 * 1. expires_at and currency inputs visible in modal
 * 2. Submit fires PATCH /api/v1/quotes/{id}
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { handlers } from "../../mocks/handlers";
import { QuoteMetadataEditModal } from "@/features/quotes/components/QuoteMetadataEditModal";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/quotes/q-1",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "q-1" }),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t-1",
      displayName: "Test Owner",
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

function renderModal(onClose = vi.fn()) {
  return render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <QuoteMetadataEditModal
            quoteId="q-00000001-0000-0000-0000-000000000001"
            currentExpiresAt="2026-09-30T23:59:59Z"
            currentCurrency="USD"
            open={true}
            onClose={onClose}
          />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B24 Quote Metadata Edit Modal Integration", () => {
  it("1. expires_at and currency inputs are visible", async () => {
    renderModal();
    expect(await screen.findByText("Edit Quote")).toBeInTheDocument();
    expect(screen.getByTestId("quote-expires-at-input")).toBeInTheDocument();
    expect(screen.getByTestId("quote-currency-select")).toBeInTheDocument();
  });

  it("2. Submit fires PATCH /api/v1/quotes/{id}", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(
        "/api/v1/quotes/q-00000001-0000-0000-0000-000000000001",
        async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({
            id: "q-00000001-0000-0000-0000-000000000001",
            expires_at: capturedBody.expires_at,
            currency: capturedBody.currency,
          });
        },
      ),
    );

    const onClose = vi.fn();
    renderModal(onClose);
    await screen.findByText("Edit Quote");

    fireEvent.change(screen.getByTestId("quote-expires-at-input"), {
      target: { value: "2026-12-31" },
    });
    fireEvent.change(screen.getByTestId("quote-currency-select"), {
      target: { value: "USD" },
    });

    fireEvent.click(screen.getByTestId("quote-metadata-save-btn"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
      expect(capturedBody?.currency).toBe("USD");
    });
  });
});
