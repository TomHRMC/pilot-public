/**
 * FE-B26 — QuotesPage quote_number Column Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b26/quotes_page_number.integration.test.tsx
 *
 * Tests:
 * 1. Column header reads "Quote #" (not "Quote ID")
 * 2. Row renders quote_number value (e.g. QUO-000001), not UUID slice
 */

import { render, screen } from "@testing-library/react";
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
import { QuotesPage } from "@/features/quotes/components/QuotesPage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/quotes",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...(rest as Record<string, unknown>)}>
      {children}
    </a>
  ),
}));

const MOCK_QUOTE_ID = "q-b26-00000001-0000-0000-0000-000000000001";

const QUOTES_OVERRIDE = [
  {
    id: MOCK_QUOTE_ID,
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    customer_name: "Smith Electric",
    site_id: "site-1",
    status_id: "status-uuid-001",
    status_code: "draft",
    quote_number: "QUO-000001",
    subtotal_cents: 185000,
    tax_cents: 14800,
    total_cents: 199800,
  },
];

// Place specific override FIRST to win over global quotesListHandlers
// UI-FIX-1C: quotes handler now returns paginated shape
const server = setupServer(
  http.get("/api/v1/quotes", () =>
    HttpResponse.json({
      items: QUOTES_OVERRIDE,
      total: QUOTES_OVERRIDE.length,
      limit: 25,
      offset: 0,
    }),
  ),
  ...handlers,
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t-1",
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

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderQuotesPage() {
  return render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <QuotesPage />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B26 QuotesPage Quote Number Column", () => {
  it("1. Column header reads 'Quote #' (not 'Quote ID')", async () => {
    renderQuotesPage();
    expect(await screen.findByText("Quote #")).toBeInTheDocument();
    expect(screen.queryByText("Quote ID")).not.toBeInTheDocument();
  });

  it("2. Row renders quote_number value 'QUO-000001'", async () => {
    renderQuotesPage();
    expect(await screen.findByText("QUO-000001")).toBeInTheDocument();
  });

  it("3. UUID slice NOT rendered in quote number column", async () => {
    renderQuotesPage();
    // Wait for data to load
    await screen.findByText("QUO-000001");
    // The first 8 chars of the UUID should NOT appear as the primary link text
    // (the UUID starts with "q-b26-00" which would be truncated)
    expect(screen.queryByText("q-b26-00…")).not.toBeInTheDocument();
  });

  it("4. Quote number links to the quote detail page", async () => {
    renderQuotesPage();
    const link = await screen.findByText("QUO-000001");
    expect(link.closest("a")).toHaveAttribute(
      "href",
      `/quotes/${MOCK_QUOTE_ID}`,
    );
  });
});
