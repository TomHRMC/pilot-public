/**
 * quoteSend integration test — FE-B19
 *
 * Location: apps/web/src/__tests__/batch_fe_b19/quoteSend.integration.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react + MSW node)
 *
 * Enforces the always-preview-before-send platform pattern:
 *   1. "Send to Customer" button opens SendQuotePreviewModal
 *   2. "Cancel" closes modal WITHOUT firing useGeneratePublicLink
 *   3. "Confirm Send" fires the public-link mutation
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import {
  quoteBuilderHandlers,
  MOCK_PUBLIC_LINK_RESPONSE,
} from "@/mocks/handlers/quoteBuilderHandlers";
import { QuoteActionBar } from "@/features/quotes/components/QuoteActionBar";

// Per-test MSW server
const server = setupServer(...quoteBuilderHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// --- Auth context helper ---
function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@pilot.example.com",
      role,
      tenantId: "t1",
      displayName: "Test Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

// --- Mock Next.js router ---
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/quotes/q-00000001-0000-0000-0000-000000000001",
  useRouter: () => ({ push: mockPush }),
}));

afterEach(() => {
  mockPush.mockClear();
});

const QUOTE_ID = "q-00000001-0000-0000-0000-000000000001";
const VERSION_ID = "qv-00000001-0000-0000-0000-000000000001";

function renderActionBar(role: "owner" | "technician" = "owner") {
  return render(
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        <QuoteActionBar
          quoteId={QUOTE_ID}
          status="draft"
          customerAcceptedAt={null}
          customerEmail="mike@smithelectrical.example.com"
          customerName="Smith Electrical"
          quoteVersionId={VERSION_ID}
          testID="test-action-bar"
        />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B19 — Always-Preview-Before-Send", () => {
  it("Send to Customer button is visible for owner on draft quote", () => {
    renderActionBar("owner");
    expect(
      screen.getByRole("button", { name: /send to customer/i }),
    ).toBeInTheDocument();
  });

  it("clicking Send to Customer opens SendQuotePreviewModal", () => {
    renderActionBar("owner");
    fireEvent.click(screen.getByRole("button", { name: /send to customer/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Smith Electrical/i)).toBeInTheDocument();
    expect(screen.getByText(/mike@smithelectrical\.com/i)).toBeInTheDocument();
  });

  it("Cancel closes modal WITHOUT firing public-link mutation", async () => {
    let publicLinkCalled = false;
    server.use(
      http.post(
        `/api/v1/quotes/${QUOTE_ID}/versions/${VERSION_ID}/public-link`,
        () => {
          publicLinkCalled = true;
          return HttpResponse.json(MOCK_PUBLIC_LINK_RESPONSE, { status: 201 });
        },
      ),
    );

    renderActionBar("owner");
    fireEvent.click(screen.getByRole("button", { name: /send to customer/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    // Modal should close
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // Public link must NOT have been called
    expect(publicLinkCalled).toBe(false);
  });

  it("Confirm Send fires public-link mutation", async () => {
    let publicLinkCalled = false;
    server.use(
      http.post(
        `/api/v1/quotes/${QUOTE_ID}/versions/${VERSION_ID}/public-link`,
        () => {
          publicLinkCalled = true;
          return HttpResponse.json(MOCK_PUBLIC_LINK_RESPONSE, { status: 201 });
        },
      ),
    );

    renderActionBar("owner");
    fireEvent.click(screen.getByRole("button", { name: /send to customer/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirm send/i }));

    await waitFor(() => {
      expect(publicLinkCalled).toBe(true);
    });
  });
});
