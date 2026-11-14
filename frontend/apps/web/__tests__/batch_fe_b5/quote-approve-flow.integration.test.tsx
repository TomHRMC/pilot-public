/**
 * Quote approve flow integration tests
 *
 * Location: apps/web/__tests__/batch_fe_b5/quote-approve-flow.integration.test.tsx
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";

// FE-B26: QuoteDetailPage now uses useRouter for "Create Job from Quote" navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/quotes/q1",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "q1" }),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QuoteDetailPage } from "@/features/quote-approval/QuoteDetailPage";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

const QUOTE_FIXTURE = {
  id: "q1",
  quote_number: "Q-2025-001",
  status: "pending_approval",
  submitted_by_user_id: "t1",
  submitted_by_name: "Jake Torres",
  customer_id: "c1",
  customer_name: "Johnson Electric",
  site_id: "site-1",
  line_items: [
    {
      id: "line-1",
      description: "200A Panel Upgrade",
      customer_visible: true,
      unit_price_cents: 150000,
      quantity: 1,
      total_cents: 150000,
      line_type: "deliverable",
    },
  ],
  subtotal_cents: 150000,
  tax_cents: 10000,
  total_cents: 160000,
  margin_percent: 40.0,
  submitted_at: new Date().toISOString(),
  approved_at: null,
  rejected_at: null,
  quote_version_id: "qv-1",
  has_owner_edits: false,
  require_approval: true,
};

const server = setupServer(
  // aggregated detail endpoint — PRE-WS3-FIX-01
  http.get("/api/v1/quotes/q1/detail", () => HttpResponse.json(QUOTE_FIXTURE)),
  http.get("/api/v1/quotes/q1/pending-edits", () => HttpResponse.json([])),
  http.get("/api/v1/quotes/q1/comments", () => HttpResponse.json([])),
  http.post("/api/v1/quotes/q1/approve", () =>
    HttpResponse.json({
      id: "q1",
      status: "approved",
      quote_version_id: "qv-2",
      approved_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function ownerAuth(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "o@t.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderQuoteDetail(id = "q1") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <AuthContext.Provider value={ownerAuth()}>
      <QueryClientProvider client={qc}>
        <QuoteDetailPage quoteId={id} />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("QuoteDetailPage approve flow integration", () => {
  it("loads quote detail with pending_approval status", async () => {
    renderQuoteDetail();
    await waitFor(() => {
      expect(screen.getByText("Quote #Q-2025-001")).toBeTruthy();
      expect(screen.getByText(/Johnson Electric/)).toBeTruthy();
    });
  });

  it("shows review mode bar for owner on pending_approval quote", async () => {
    renderQuoteDetail();
    await waitFor(() => {
      expect(screen.getByTestId("quote-review-mode-bar")).toBeTruthy();
    });
  });

  it("Approve button visible for owner on pending_approval quote", async () => {
    renderQuoteDetail();
    await waitFor(() => {
      expect(screen.getByTestId("approve-btn")).toBeTruthy();
    });
  });

  it("clicking Approve calls approve mutation", async () => {
    let approveCalled = false;
    server.use(
      http.post("/api/v1/quotes/q1/approve", () => {
        approveCalled = true;
        return HttpResponse.json({
          id: "q1",
          status: "approved",
          quote_version_id: "qv-2",
          approved_at: new Date().toISOString(),
        });
      }),
    );

    renderQuoteDetail();
    await waitFor(() => screen.getByTestId("approve-btn"));
    fireEvent.click(screen.getByTestId("approve-btn"));
    await waitFor(() => expect(approveCalled).toBe(true));
  });

  it("staleness: 409 response opens StalenessDialog", async () => {
    server.use(
      http.post("/api/v1/quotes/q1/approve", () =>
        HttpResponse.json(
          {
            status: 409,
            title: "Record updated since last view",
            detail: "Another user updated this quote",
            refreshed_state: { quote_version_id: "qv-2", line_items: [] },
          },
          { status: 409 },
        ),
      ),
    );

    renderQuoteDetail();
    await waitFor(() => screen.getByTestId("approve-btn"));
    fireEvent.click(screen.getByTestId("approve-btn"));

    await waitFor(() => {
      // StalenessDialog should render when 409 received
      expect(
        screen.queryByText(/was updated/i) ?? screen.queryByText(/retry/i),
      ).toBeTruthy();
    });
  });
});
