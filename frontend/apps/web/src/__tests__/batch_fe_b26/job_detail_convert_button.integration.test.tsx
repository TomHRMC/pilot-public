/**
 * FE-B26 — JobDetailPage Convert Button Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b26/job_detail_convert_button.integration.test.tsx
 *
 * Tests:
 * 1. "Create Invoice" button visible when job.status_code === "completed"
 * 2. "Create Invoice" button NOT visible when job.status_code === "draft"
 * 3. Clicking "Create Invoice" navigates to /invoices/new?job_id={id}
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
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { handlers } from "../../mocks/handlers";
import { JobDetailPage } from "@/features/jobs/components/JobDetailPage";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs/job-b26-completed",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "job-b26-completed" }),
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

const makeJobFixture = (id: string, statusCode: string) => ({
  id,
  tenant_id: "tenant-1",
  customer_id: "cust-1",
  site_id: "site-1",
  status_id: "status-uuid-001",
  status_code: statusCode,
  job_number: `JOB-B26-${statusCode.slice(0, 3)}`,
  site_name: "Test Site",
  customer_name: "Test Customer",
  quote_id: null,
  scheduled_start_at: "2026-07-14T08:00:00Z",
  scheduled_end_at: "2026-07-14T16:00:00Z",
  estimated_duration_minutes: 480,
  actual_labor_cost_cents: 50000,
  actual_material_cost_cents: 25000,
  actual_profit_cents: 15000,
  is_active: true,
});

// Specific job handlers FIRST — before global handlers to avoid route conflict
const server = setupServer(
  http.get("/api/v1/jobs/job-b26-completed", () =>
    HttpResponse.json(makeJobFixture("job-b26-completed", "completed")),
  ),
  http.get("/api/v1/jobs/job-b26-draft", () =>
    HttpResponse.json(makeJobFixture("job-b26-draft", "draft")),
  ),
  ...handlers,
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  mockPush.mockClear();
});
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

function renderJobDetail(jobId: string) {
  return render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <JobDetailPage jobId={jobId} />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B26 JobDetailPage Convert Button", () => {
  it("1. 'Create Invoice' button visible when status_code === 'completed'", async () => {
    renderJobDetail("job-b26-completed");
    expect(
      await screen.findByTestId("convert-to-invoice-btn"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("convert-to-invoice-btn")).toHaveTextContent(
      "Create Invoice",
    );
  });

  it("2. 'Create Invoice' button NOT visible when status_code === 'draft'", async () => {
    renderJobDetail("job-b26-draft");
    // Wait for job to load by checking header renders the job_number
    await screen.findByText("JOB-B26-dra");
    expect(
      screen.queryByTestId("convert-to-invoice-btn"),
    ).not.toBeInTheDocument();
  });

  it("3. Clicking 'Create Invoice' navigates to /invoices/new?job_id={id}", async () => {
    renderJobDetail("job-b26-completed");
    const btn = await screen.findByTestId("convert-to-invoice-btn");
    fireEvent.click(btn);
    expect(mockPush).toHaveBeenCalledWith(
      "/invoices/new?job_id=job-b26-completed",
    );
  });
});
