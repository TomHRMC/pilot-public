/**
 * FE-B26 — JobDetailHeader UUID Fixes Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b26/job_detail_header.integration.test.tsx
 *
 * Tests:
 * 1. Renders job_number in breadcrumb (not raw UUID)
 * 2. Renders correct status badge label from status_code
 * 3. Renders site_name (not site UUID)
 * 4. Renders customer_name
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
import { handlers } from "../../mocks/handlers";
import { JobDetailHeader } from "@/features/jobs/components/JobDetailHeader";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs/job-b26-001",
  useSearchParams: () => new URLSearchParams(),
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

const mockJobDetail = {
  id: "job-b26-001",
  tenant_id: "tenant-1",
  customer_id: "cust-1",
  site_id: "site-uuid-001",
  status_id: "status-uuid-001",
  status_code: "in_progress",
  job_number: "JOB-000001",
  site_name: "The Smith Home",
  customer_name: "Acme Electric",
  quote_id: "quote-uuid-001",
  scheduled_start_at: "2026-07-14T08:00:00Z",
  scheduled_end_at: "2026-07-14T16:00:00Z",
  estimated_duration_minutes: 480,
  actual_labor_cost_cents: 50000,
  actual_material_cost_cents: 25000,
  actual_profit_cents: 15000,
  is_active: true,
};

// Place specific handlers BEFORE global handlers so they match first (MSW FIFO)
const server = setupServer(
  http.get("/api/v1/jobs/job-b26-001", () => HttpResponse.json(mockJobDetail)),
  http.get("/api/v1/jobs/job-b26-null", () =>
    HttpResponse.json({
      ...mockJobDetail,
      id: "job-b26-null",
      job_number: null,
    }),
  ),
  ...handlers,
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderHeader(jobId = "job-b26-001") {
  return render(
    <QueryClientProvider client={makeQC()}>
      <JobDetailHeader jobId={jobId} />
    </QueryClientProvider>,
  );
}

describe("FE-B26 JobDetailHeader UUID Fixes", () => {
  it("1. Renders job_number in breadcrumb (not raw UUID)", async () => {
    renderHeader();
    expect(await screen.findByText("JOB-000001")).toBeInTheDocument();
    // Should NOT show the raw UUID
    expect(screen.queryByText("job-b26-001")).not.toBeInTheDocument();
  });

  it("2. Renders correct status badge label from status_code", async () => {
    renderHeader();
    expect(await screen.findByText("In Progress")).toBeInTheDocument();
  });

  it("3. Renders site_name (not site UUID)", async () => {
    renderHeader();
    expect(await screen.findByText("📍 The Smith Home")).toBeInTheDocument();
    // Should NOT show the raw UUID
    expect(screen.queryByText("site-uuid-001")).not.toBeInTheDocument();
  });

  it("4. Renders customer_name", async () => {
    renderHeader();
    expect(await screen.findByText("Acme Electric")).toBeInTheDocument();
  });

  it("5. Renders 'View Quote →' link when quote_id is present", async () => {
    renderHeader();
    const quoteLink = await screen.findByText("View Quote →");
    expect(quoteLink).toBeInTheDocument();
    expect(quoteLink.closest("a")).toHaveAttribute(
      "href",
      "/quotes/quote-uuid-001",
    );
  });

  it("6. Fallback to UUID slice when job_number is null", async () => {
    renderHeader("job-b26-null");
    // Should show fallback: "Job job-b26…" (first 8 chars + ellipsis)
    expect(await screen.findByText(/Job job-b26/)).toBeInTheDocument();
  });
});
