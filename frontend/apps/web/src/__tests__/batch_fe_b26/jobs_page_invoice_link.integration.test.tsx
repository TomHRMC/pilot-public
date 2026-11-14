/**
 * FE-B26 — JobsPage "Create Invoice" Link Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b26/jobs_page_invoice_link.integration.test.tsx
 *
 * Tests:
 * 1. "Create Invoice" link href contains /invoices/new?job_id= (not ?action=convert)
 * 2. "Create Invoice" link visible only for completed/invoice_pending jobs
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
import { JobsPage } from "@/features/jobs/components/JobsPage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs",
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

const COMPLETED_JOB_ID = "job-b26-inv-001";

const JOB_LIST_OVERRIDE = [
  {
    id: COMPLETED_JOB_ID,
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    status_id: "status-completed",
    status_code: "completed",
    job_number: "JOB-INV-001",
    customer_name: "Completed Customer",
    scheduled_start_at: "2026-07-01T08:00:00Z",
    scheduled_end_at: "2026-07-01T16:00:00Z",
    estimated_duration_minutes: 480,
  },
  {
    id: "job-b26-inv-002",
    tenant_id: "tenant-1",
    customer_id: "cust-2",
    site_id: "site-2",
    status_id: "status-draft",
    status_code: "draft",
    job_number: "JOB-INV-002",
    customer_name: "Draft Customer",
    scheduled_start_at: null,
    scheduled_end_at: null,
    estimated_duration_minutes: null,
  },
];

// Place specific override FIRST so it wins over global jobs handler
// UI-FIX-1C: jobs handler now returns paginated shape
const server = setupServer(
  http.get("/api/v1/jobs/", () =>
    HttpResponse.json({
      items: JOB_LIST_OVERRIDE,
      total: JOB_LIST_OVERRIDE.length,
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

function renderJobsPage() {
  return render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <JobsPage />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B26 JobsPage Invoice Link", () => {
  it("1. 'Create Invoice' link has href /invoices/new?job_id= (not ?action=convert)", async () => {
    renderJobsPage();
    const link = await screen.findByText("Create Invoice");
    expect(link.closest("a")).toHaveAttribute(
      "href",
      `/invoices/new?job_id=${COMPLETED_JOB_ID}`,
    );
    // Old broken href pattern should NOT be present
    expect(link.closest("a")?.getAttribute("href")).not.toContain(
      "action=convert",
    );
  });

  it("2. 'Create Invoice' link visible for completed job", async () => {
    renderJobsPage();
    expect(await screen.findByText("Create Invoice")).toBeInTheDocument();
  });

  it("3. 'Create Invoice' link NOT visible for draft job", async () => {
    renderJobsPage();
    // Wait for page to load with both customers
    await screen.findByText("Completed Customer");
    await screen.findByText("Draft Customer");
    // Should have exactly one "Create Invoice" link (the completed job only)
    const invoiceLinks = screen.getAllByText("Create Invoice");
    expect(invoiceLinks).toHaveLength(1);
  });
});
