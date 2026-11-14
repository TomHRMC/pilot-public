/**
 * FE-B26 — QuoteDetailPage "Create Job from Quote" CTA Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b26/quote_detail_create_job.integration.test.tsx
 *
 * Tests:
 * 1. "Create Job from Quote" button visible when status === "accepted" AND role is owner
 * 2. Button NOT visible for owner when status is "draft"
 * 3. Button NOT visible for tech role when status is "accepted"
 * 4. Clicking button opens JobFormModal (check for modal presence)
 */

import { render, screen, fireEvent } from "@testing-library/react";
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
import type { PilotRole } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { handlers } from "../../mocks/handlers";
import { QuoteDetailPage } from "@/features/quote-approval/QuoteDetailPage";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/quotes/quote-b26-001",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "quote-b26-001" }),
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

const BASE_QUOTE_DETAIL = {
  id: "quote-b26-accepted",
  tenant_id: "tenant-1",
  customer_id: "cust-1",
  customer_name: "Smith Electric",
  submitted_by_name: "Mike Smith",
  site_id: "site-1",
  status_id: "status-uuid-001",
  status: "accepted",
  status_code: "accepted",
  quote_number: "QUO-000001",
  subtotal_cents: 185000,
  tax_cents: 14800,
  total_cents: 199800,
  currency: "USD",
  margin_percent: 42.5,
  quote_version_id: "qv-00000001",
  has_owner_edits: false,
  require_approval: false,
  line_items: [],
  is_active: true,
  expires_at: null,
};

// Specific handlers FIRST to win over any global quote detail handlers
const server = setupServer(
  http.get("/api/v1/quotes/quote-b26-accepted/detail", () =>
    HttpResponse.json({
      ...BASE_QUOTE_DETAIL,
      id: "quote-b26-accepted",
      status: "accepted",
      status_code: "accepted",
    }),
  ),
  http.get("/api/v1/quotes/quote-b26-draft/detail", () =>
    HttpResponse.json({
      ...BASE_QUOTE_DETAIL,
      id: "quote-b26-draft",
      status: "draft",
      status_code: "draft",
    }),
  ),
  ...handlers,
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  mockPush.mockClear();
});
afterAll(() => server.close());

function makeAuth(role: PilotRole): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: `${role}@test.com`,
      role,
      tenantId: "t-1",
      displayName: "Test User",
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

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderPage(quoteId: string, role: PilotRole = "owner") {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <QuoteDetailPage quoteId={quoteId} />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B26 QuoteDetailPage Create Job CTA", () => {
  it("1. 'Create Job from Quote' button visible for owner when status === 'accepted'", async () => {
    renderPage("quote-b26-accepted", "owner");
    expect(
      await screen.findByTestId("create-job-from-quote-btn"),
    ).toBeInTheDocument();
  });

  it("2. Button NOT visible for owner when status === 'draft'", async () => {
    renderPage("quote-b26-draft", "owner");
    // Wait for quote to load — look for quote number which is always standalone text
    await screen.findByText("Quote #QUO-000001");
    expect(
      screen.queryByTestId("create-job-from-quote-btn"),
    ).not.toBeInTheDocument();
  });

  it("3. Button NOT visible for tech role when status === 'accepted'", async () => {
    renderPage("quote-b26-accepted", "technician");
    // tech cannot see "Create Job" — RoleGate hides it
    // Wait for the quote to at least load
    await screen.findByText("Quote #QUO-000001");
    expect(
      screen.queryByTestId("create-job-from-quote-btn"),
    ).not.toBeInTheDocument();
  });

  it("4. Clicking button opens JobFormModal (dialog appears)", async () => {
    renderPage("quote-b26-accepted", "owner");
    const btn = await screen.findByTestId("create-job-from-quote-btn");
    fireEvent.click(btn);
    // JobFormModal renders with role="dialog"
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    // Modal title should be "Add Job"
    expect(await screen.findByText("Add Job")).toBeInTheDocument();
  });
});
