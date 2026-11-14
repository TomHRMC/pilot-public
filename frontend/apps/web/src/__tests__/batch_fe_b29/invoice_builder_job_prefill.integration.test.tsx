/**
 * FE-B29 Integration — Invoice Builder Job Pre-fill
 *
 * Location: apps/web/src/__tests__/batch_fe_b29/invoice_builder_job_prefill.integration.test.tsx
 *
 * Tests:
 * 1. When jobId prop passed, billable items render after load
 * 2. Linked job amber badge shows job number
 * 3. Line item rows show tech entry ("Jake Rodriguez") and expense ("Wire 12AWG 50ft")
 * 4. Dismissing [×] on amber badge hides the linked job badge
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
  beforeEach,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser } from "@pilot/ui/auth";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Navigation mock ───────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  usePathname: () => "/invoices/new",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));
beforeEach(() => {
  mockPush.mockClear();
  mockBack.mockClear();
});

// ── MSW ───────────────────────────────────────────────────────────────────────

const TEST_JOB_ID = "job-00000001-0000-0000-0000-000000000001";

const MOCK_JOB = {
  id: TEST_JOB_ID,
  tenant_id: "t-00000001",
  customer_id: "c-00000001-0000-0000-0000-000000000001",
  site_id: "s-00000001-0000-0000-0000-000000000001",
  status_id: "st-completed",
  status_code: "completed",
  job_number: "JOB-000001",
  customer_name: "Acme Electric",
  site_name: "Main Site",
  scheduled_start_at: null,
  scheduled_end_at: null,
  estimated_duration_minutes: null,
  external_calendar_event_id: null,
  actual_labor_cost_cents: 34000,
  actual_material_cost_cents: 4800,
  actual_profit_cents: 10000,
  is_active: true,
};

const MOCK_BILLABLE_ITEMS = {
  job_id: TEST_JOB_ID,
  job_number: "JOB-000001",
  customer_name: "Acme Electric",
  time_entries: [
    {
      id: "te-00000001-0000-0000-0000-000000000001",
      user_id: "u-00000001-0000-0000-0000-000000000001",
      tech_name: "Jake Rodriguez",
      started_at: "2026-07-01T08:00:00Z",
      ended_at: "2026-07-01T12:00:00Z",
      hours: "4.00",
      hourly_rate_cents: 8500,
      total_cost_cents: 34000,
      notes: "Panel upgrade labor",
      is_already_invoiced: false,
    },
  ],
  expenses: [
    {
      id: "exp-00000001-0000-0000-0000-000000000001",
      description: "Wire 12AWG 50ft",
      cost_cents: 4800,
      billable_cents: 5280,
      is_billable: true,
      is_already_invoiced: false,
      incurred_at: "2026-07-01T09:30:00Z",
    },
  ],
};

const server = setupServer(
  http.get("/api/v1/jobs/:job_id", ({ params }) => {
    const { job_id } = params as { job_id: string };
    if (job_id === TEST_JOB_ID) return HttpResponse.json(MOCK_JOB);
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  http.get("/api/v1/jobs/:job_id/billable-items", ({ params }) => {
    const { job_id } = params as { job_id: string };
    if (job_id === TEST_JOB_ID) return HttpResponse.json(MOCK_BILLABLE_ITEMS);
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  // useCustomers expects a plain array (res.data as CustomerListItem[]) — NOT {items, total}
  http.get("/api/v1/customers/", () => HttpResponse.json([])),
  http.get("/api/v1/customers/:customerId/sites", () => HttpResponse.json([])),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(): AuthContextValue {
  const user: PilotUser = {
    id: "u-00000001",
    email: "test@pilot.example.com",
    role: "owner",
    tenantId: "t-00000001",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue()}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InvoiceBuilderPage — job pre-fill", () => {
  it("1. when jobId prop passed, billable items render after load", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText(/Jake Rodriguez/i)).toBeInTheDocument();
    });
  });

  it("2. linked job amber badge shows job number", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText(/JOB-000001/i)).toBeInTheDocument();
    });
  });

  it("3. line item rows show tech entry and expense description", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText(/Jake Rodriguez/i)).toBeInTheDocument();
      expect(screen.getByText(/Wire 12AWG 50ft/i)).toBeInTheDocument();
    });
  });

  it("4. clicking Clear job hides the linked job badge (PLP-FIX-5)", async () => {
    // PLP-FIX-5 (Issue 13b): no confirm dialog; "Clear job" button replaces dismiss
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });
    // Wait for badge to appear
    await waitFor(() => {
      expect(screen.getByText(/JOB-000001/i)).toBeInTheDocument();
    });
    // Click Clear job button
    fireEvent.click(screen.getByRole("button", { name: /Clear job/i }));
    // Badge should be gone
    await waitFor(() => {
      expect(screen.queryByText(/JOB-000001/i)).not.toBeInTheDocument();
    });
  });
});
