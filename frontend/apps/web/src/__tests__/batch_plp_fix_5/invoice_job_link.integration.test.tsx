/**
 * PLP-FIX-5 Part B — Invoice Builder Job-Link (Issue 13b)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_5/invoice_job_link.integration.test.tsx
 *
 * Tests:
 * 1. Job-link selector appears when customer set + no active job
 * 2. Selecting a job sets the linked chip + triggers prefill flow
 * 3. Clear job returns to standalone (selector reappears)
 * 4. Job-link selector NOT visible when no customer selected
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
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

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

// ── Fixtures ──────────────────────────────────────────────────────────────────

const CUSTOMER_ID = "c-00000001-0000-0000-0000-000000000001";
const SITE_ID = "s-00000001-0000-0000-0000-000000000001";
const JOB_ID = "job-00000001-0000-0000-0000-000000000001";

const MOCK_JOB = {
  id: JOB_ID,
  tenant_id: "t-1",
  customer_id: CUSTOMER_ID,
  site_id: SITE_ID,
  status_id: "st-completed",
  status_code: "completed",
  job_number: "JOB-000001",
  customer_name: "Acme Electric",
  site_name: "Main Site",
  title: "Panel Upgrade",
  scheduled_start_at: null,
  scheduled_end_at: null,
  estimated_duration_minutes: null,
  external_calendar_event_id: null,
  actual_labor_cost_cents: 34000,
  actual_material_cost_cents: 4800,
  actual_profit_cents: 10000,
  is_active: true,
};

const MOCK_JOBS_LIST = {
  items: [MOCK_JOB],
  total: 1,
  limit: 20,
  offset: 0,
};

const MOCK_BILLABLE_ITEMS = {
  job_id: JOB_ID,
  job_number: "JOB-000001",
  customer_name: "Acme Electric",
  time_entries: [],
  expenses: [],
};

const MOCK_CUSTOMER = {
  id: CUSTOMER_ID,
  display_name: "Acme Electric",
  customer_type: "company",
  email: null,
  phone: null,
  is_active: true,
};

// ── MSW ──────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/jobs/:job_id", ({ params }) => {
    const { job_id } = params as { job_id: string };
    if (job_id === JOB_ID) return HttpResponse.json(MOCK_JOB);
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  http.get("/api/v1/jobs/", ({ request }) => {
    const url = new URL(request.url);
    const customerId = url.searchParams.get("customer_id");
    if (customerId === CUSTOMER_ID) {
      return HttpResponse.json(MOCK_JOBS_LIST);
    }
    return HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 });
  }),
  http.get("/api/v1/jobs/:job_id/billable-items", ({ params }) => {
    const { job_id } = params as { job_id: string };
    if (job_id === JOB_ID) return HttpResponse.json(MOCK_BILLABLE_ITEMS);
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  http.get("/api/v1/customers/", () =>
    HttpResponse.json({
      items: [MOCK_CUSTOMER],
      total: 1,
      limit: 200,
      offset: 0,
    }),
  ),
  http.get("/api/v1/customers/:customerId/sites", () =>
    HttpResponse.json([
      { id: SITE_ID, name: "Main Site", address: { line1: "123 Main St" } },
    ]),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuthValue(): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "test@pilot.example.com",
      role: "owner",
      tenantId: "t-1",
      displayName: "Test User",
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

// Helper: select a customer in the combobox
async function selectCustomer(displayName: string) {
  const customerInput = await screen.findByLabelText("Customer");
  await waitFor(() => expect(customerInput).not.toBeDisabled());
  fireEvent.focus(customerInput);
  fireEvent.change(customerInput, { target: { value: displayName } });
  await waitFor(() => {
    expect(screen.getByText(displayName)).toBeInTheDocument();
  });
  fireEvent.mouseDown(screen.getByText(displayName));
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-5 — Invoice Builder Job-Link (Issue 13b)", () => {
  it("1. job-link selector appears when customer set + no active job", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });

    await selectCustomer("Acme Electric");

    // Job-link selector should appear
    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-job-link-selector"),
      ).toBeInTheDocument();
    });
  });

  it("2. selecting a job sets the linked chip + triggers prefill", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });

    await selectCustomer("Acme Electric");

    // Wait for job-link selector
    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-job-link-selector"),
      ).toBeInTheDocument();
    });

    // Type in the job combobox to filter and select
    const jobInput = screen.getByRole("combobox", { name: "Job" });
    fireEvent.focus(jobInput);
    fireEvent.change(jobInput, { target: { value: "JOB" } });

    await waitFor(() => {
      expect(screen.getByText(/JOB-000001/i)).toBeInTheDocument();
    });

    // Click the job option
    fireEvent.mouseDown(screen.getByText(/JOB-000001/i));

    // The linked job badge should appear (chip)
    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-source-job-badge"),
      ).toBeInTheDocument();
    });
  });

  it("3. Clear job returns to standalone (selector reappears)", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });

    await selectCustomer("Acme Electric");

    // Select a job
    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-job-link-selector"),
      ).toBeInTheDocument();
    });
    const jobInput = screen.getByRole("combobox", { name: "Job" });
    fireEvent.focus(jobInput);
    fireEvent.change(jobInput, { target: { value: "JOB" } });
    await waitFor(() => {
      expect(screen.getByText(/JOB-000001/i)).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByText(/JOB-000001/i));

    // Badge appears
    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-source-job-badge"),
      ).toBeInTheDocument();
    });

    // Click Clear job
    fireEvent.click(screen.getByRole("button", { name: /Clear job/i }));

    // Badge removed
    await waitFor(() => {
      expect(
        screen.queryByTestId("invoice-source-job-badge"),
      ).not.toBeInTheDocument();
    });

    // Selector reappears
    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-job-link-selector"),
      ).toBeInTheDocument();
    });
  });

  it("4. job-link selector NOT visible when no customer selected", () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });

    // No customer selected yet — selector should NOT be visible
    expect(
      screen.queryByTestId("invoice-job-link-selector"),
    ).not.toBeInTheDocument();
  });
});
