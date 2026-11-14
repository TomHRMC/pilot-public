/**
 * PLP-FIX-2 Integration — Customer Jobs New Job Modal
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_2/customer_jobs_new_job_modal.integration.test.tsx
 *
 * Issue-3 integration: customer Jobs tab — clicking customer-jobs-new-btn opens
 * a role="dialog"; customer combobox is preselected with the page's customer;
 * select a site, submit → POST /api/v1/jobs/ body contains that customer_id +
 * site_id; tech role does NOT see the button (RoleGate).
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
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { CustomerJobsList } from "@/features/customers/components/CustomerJobsList";

// ── Navigation mock ──────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/customers/cust-1/jobs",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// ── MSW ───────────────────────────────────────────────────────────────────────

const MOCK_JOBS = [
  {
    id: "job-1",
    tenant_id: "t-1",
    customer_id: "cust-1",
    site_id: "s-1",
    status_id: "st-scheduled",
    status_code: "scheduled",
    customer_name: "Apex Commercial LLC",
    job_number: "JOB-000001",
    title: "Panel upgrade",
    scheduled_start_at: "2026-07-24T09:00:00Z",
    scheduled_end_at: null,
    estimated_duration_minutes: 240,
    recurrence_rule_id: null,
  },
];

const server = setupServer(
  // GET /api/v1/jobs/ — list jobs for the customer
  http.get("/api/v1/jobs/", ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get("customer_id") === "cust-1") {
      return HttpResponse.json({
        items: MOCK_JOBS,
        total: 1,
        limit: 25,
        offset: 0,
      });
    }
    return HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 });
  }),
  // GET /api/v1/customers/ — for CustomerCombobox inside JobFormModal (paginated)
  http.get("/api/v1/customers/", () =>
    HttpResponse.json({
      items: [
        {
          id: "cust-1",
          tenant_id: "t-1",
          type: "company",
          display_name: "Apex Commercial LLC",
          first_name: null,
          last_name: null,
          company_name: "Apex Commercial LLC",
          email: null,
          mobile_phone: null,
        },
      ],
      total: 1,
      limit: 200,
      offset: 0,
    }),
  ),
  // GET /api/v1/sites/ — for SiteCombobox inside JobFormModal (filtered by customer_id)
  http.get("/api/v1/sites/", ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get("customer_id") === "cust-1") {
      return HttpResponse.json([
        {
          id: "s-1",
          customer_id: "cust-1",
          name: "Main Site",
          address: null,
          is_active: true,
        },
      ]);
    }
    return HttpResponse.json([]);
  }),
  // POST /api/v1/jobs/ — capture the body
  http.post("/api/v1/jobs/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "job-new-001",
        tenant_id: "t-1",
        customer_id: body.customer_id,
        site_id: body.site_id,
        status_id: "st-draft",
        scheduled_start_at: body.scheduled_start_at ?? null,
        scheduled_end_at: body.scheduled_end_at ?? null,
        estimated_duration_minutes: body.estimated_duration_minutes ?? null,
        actual_labor_cost_cents: 0,
        actual_material_cost_cents: 0,
        actual_profit_cents: 0,
        is_active: true,
      },
      { status: 201 },
    );
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(
  role: "owner" | "technician" = "owner",
): AuthContextValue {
  const user: PilotUser = {
    id: "u-00000001",
    email: "test@pilot.example.com",
    role,
    tenantId: "t-00000001",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper(role: "owner" | "technician" = "owner") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue(role)}>
        <QueryClientProvider client={queryClient}>
          <NotificationQueueProvider>{children}</NotificationQueueProvider>
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PLP-FIX-2 — Customer Jobs New Job Modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clicking customer-jobs-new-btn opens a role=dialog (Issue 3)", async () => {
    const Wrapper = createWrapper("owner");
    render(<CustomerJobsList customerId="cust-1" />, { wrapper: Wrapper });

    // Wait for jobs to load
    await waitFor(() => {
      expect(screen.getByText("JOB-000001")).toBeInTheDocument();
    });

    // Click the New Job button
    const newJobBtn = screen.getByTestId("customer-jobs-new-btn");
    fireEvent.click(newJobBtn);

    // A dialog should appear
    await waitFor(() => {
      expect(
        screen.getByRole("dialog", { name: /add job/i }),
      ).toBeInTheDocument();
    });
  });

  it("customer combobox is preselected with the page's customer (Issue 3)", async () => {
    const Wrapper = createWrapper("owner");
    render(<CustomerJobsList customerId="cust-1" />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("JOB-000001")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("customer-jobs-new-btn"));

    // Wait for the modal to open and the customer combobox to be preselected
    await waitFor(() => {
      expect(
        screen.getByRole("dialog", { name: /add job/i }),
      ).toBeInTheDocument();
    });

    // The customer combobox input should show the preselected customer's name
    await waitFor(() => {
      const customerInput = screen.getByDisplayValue(/Apex Commercial LLC/i);
      expect(customerInput).toBeInTheDocument();
    });
  });

  it("select a site, submit → POST /api/v1/jobs/ body contains customer_id + site_id", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/jobs/", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "job-new-002",
            tenant_id: "t-1",
            customer_id: "cust-1",
            site_id: "s-1",
            status_id: "st-draft",
            scheduled_start_at: null,
            scheduled_end_at: null,
            estimated_duration_minutes: null,
            actual_labor_cost_cents: 0,
            actual_material_cost_cents: 0,
            actual_profit_cents: 0,
            is_active: true,
          },
          { status: 201 },
        );
      }),
    );

    const Wrapper = createWrapper("owner");
    render(<CustomerJobsList customerId="cust-1" />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("JOB-000001")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("customer-jobs-new-btn"));

    // Wait for the modal to open
    await waitFor(() => {
      expect(
        screen.getByRole("dialog", { name: /add job/i }),
      ).toBeInTheDocument();
    });

    // The site combobox needs to load sites and then be focused to open
    const siteInput = await screen.findByRole("combobox", { name: /site/i });
    // Wait for the site combobox to be enabled (customer selected + sites loaded)
    await waitFor(() => {
      expect(siteInput).not.toBeDisabled();
    });
    // Open the dropdown by focusing + changing input to trigger open state
    fireEvent.focus(siteInput);
    fireEvent.change(siteInput, { target: { value: "Main" } });

    // Wait for the site option to appear, then select it
    const siteOption = await screen.findByRole("option", { name: "Main Site" });
    fireEvent.mouseDown(siteOption);

    // Submit the form
    const submitBtn = screen.getByTestId("job-submit-btn");
    fireEvent.click(submitBtn);

    await waitFor(() => expect(capturedBody).not.toBeNull());
    expect(capturedBody!.customer_id).toBe("cust-1");
    expect(capturedBody!.site_id).toBe("s-1");
  });

  it("tech role does NOT see the New Job button (RoleGate — hide-not-disable)", async () => {
    const Wrapper = createWrapper("technician");
    render(<CustomerJobsList customerId="cust-1" />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("JOB-000001")).toBeInTheDocument();
    });

    // The button should not be in the DOM at all (hide-not-disable, Rule 6)
    expect(
      screen.queryByTestId("customer-jobs-new-btn"),
    ).not.toBeInTheDocument();
  });
});
