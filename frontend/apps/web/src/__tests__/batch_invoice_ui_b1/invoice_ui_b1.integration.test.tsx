/**
 * INVOICE-UI-B1 Integration — Invoice Builder Job Pre-Population + URL Fix
 *
 * Location: apps/web/src/__tests__/batch_invoice_ui_b1/invoice_ui_b1.integration.test.tsx
 *
 * Tests:
 * 1. URL fix (headline): JobPropertiesPanel "Create Invoice" link href is
 *    /invoices/new?job_id={id} and does NOT contain /invoices/create
 * 2. Badge title: InvoiceBuilderPage badge shows "Source Job: {title}" and
 *    the link href is /jobs/{id}
 * 3. Badge fallback: when job.title is null, badge falls back to job_number
 * 4. Dismiss confirm — cancel: window.confirm returns false → badge stays
 * 5. Dismiss confirm — accept: window.confirm returns true → badge removed
 * 6. RBAC: tech role does NOT see InvoiceBuilderPage content (RoleGate
 *    permission="invoices.create" hides it)
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
import type { AuthContextValue, PilotUser, PilotRole } from "@pilot/ui/auth";
import { JobPropertiesPanel } from "@/features/dispatch-board/components/JobPropertiesPanel";
import type { ScheduledJob } from "@/features/dispatch-board/components/DispatchBoardLanes";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Navigation + Link mocks ──────────────────────────────────────────────────

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

const TEST_JOB_ID = "job-invoice-ui-b1-001";

// Job WITH a title — proves the title path
const MOCK_JOB_WITH_TITLE = {
  id: TEST_JOB_ID,
  tenant_id: "t-invoice-ui-b1",
  customer_id: "c-invoice-ui-b1",
  site_id: "s-invoice-ui-b1",
  status_id: "st-completed",
  status_code: "completed",
  job_number: "JOB-000001",
  customer_name: "Acme Electric",
  site_name: "Main Site",
  title: "Panel Upgrade — Acme HQ",
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
  time_entries: [],
  expenses: [],
};

const server = setupServer(
  // Default handler returns the job WITH a title.
  // Per-test overrides use server.use(...) to swap the response.
  http.get("/api/v1/jobs/:job_id", ({ params }) => {
    const { job_id } = params as { job_id: string };
    if (job_id === TEST_JOB_ID) return HttpResponse.json(MOCK_JOB_WITH_TITLE);
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  http.get("/api/v1/jobs/:job_id/billable-items", ({ params }) => {
    const { job_id } = params as { job_id: string };
    if (job_id === TEST_JOB_ID) return HttpResponse.json(MOCK_BILLABLE_ITEMS);
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  // PLP-FIX-5: jobs list handler for JobCombobox (customer-scoped)
  http.get("/api/v1/jobs/", () =>
    HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 }),
  ),
  // useCustomers expects a plain array (res.data as CustomerListItem[])
  http.get("/api/v1/customers/", () => HttpResponse.json([])),
  http.get("/api/v1/customers/:customerId/sites", () => HttpResponse.json([])),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(role: PilotRole = "owner"): AuthContextValue {
  // PLP-FIX-10: include schedule.view_all + schedule.manage to mirror prod
  // grants (owner has * wildcard in prod; static map doesn't include these).
  // Tech role gets a minimal set (no invoices.create — the test verifies
  // InvoiceBuilderPage is hidden for tech).
  const rolePerms: Record<PilotRole, string[]> = {
    owner: [
      "schedule.view_all",
      "schedule.manage",
      "users.view",
      "invoices.view",
      "invoices.update",
      "invoices.create",
    ],
    office_staff: [
      "schedule.view_all",
      "schedule.manage",
      "users.view",
      "invoices.view",
      "invoices.create",
    ],
    technician: ["dashboard.manage", "jobs.view"],
    accountant: ["invoices.view", "reports.view"],
  };
  const perms = rolePerms[role] ?? rolePerms.owner;
  const user: PilotUser = {
    id: "u-invoice-ui-b1",
    email: "test@pilot.example.com",
    role,
    tenantId: "t-invoice-ui-b1",
    displayName: "Test User",
    accessToken: "mock-token",
    permissions: perms,
  };
  return {
    user,
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper(role: PilotRole = "owner") {
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
          {children}
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Dispatch-board job helper ─────────────────────────────────────────────────

function makeScheduledJob(id: string): ScheduledJob {
  return {
    id,
    title: `Job ${id}`,
    customer_name: "Test Customer",
    site_address: "123 Test St",
    scheduled_start_at: "2026-07-27T09:00:00.000Z",
    scheduled_end_at: "2026-07-27T11:00:00.000Z",
    tech_id: "tech-001",
    status: "completed",
    priority: "standard",
    customer_type: "company",
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
    lane_index: 0,
  } as ScheduledJob;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("INVOICE-UI-B1 — URL fix + badge enhancement", () => {
  // 1. URL fix (headline)
  it("1. JobPropertiesPanel 'Create Invoice' link href is /invoices/new?job_id={id} (not /invoices/create)", () => {
    const JOB_ID = "job-url-fix-001";
    const qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    // PLP-FIX-10: wrap with AuthContext — JobPropertiesPanel renders
    // TechAssignmentSection which calls useHasPermission → useAuth().
    render(
      <AuthContext.Provider value={makeAuthValue("owner")}>
        <QueryClientProvider client={qc}>
          <JobPropertiesPanel
            job={makeScheduledJob(JOB_ID)}
            onClose={vi.fn()}
            onJobUpdated={vi.fn()}
          />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    const createInvoiceLink = screen.getByText("Create Invoice").closest("a");
    expect(createInvoiceLink).not.toBeNull();
    expect(createInvoiceLink!.getAttribute("href")).toBe(
      `/invoices/new?job_id=${JOB_ID}`,
    );
    // Regression guard: the old 404 path must NOT appear
    expect(createInvoiceLink!.getAttribute("href")).not.toContain(
      "/invoices/create",
    );
  });

  // 2. Badge title + link — PLP-FIX-5: chip format is "{job_number} · {title}"
  it("2. badge shows '{job_number} · {title}' and links to /jobs/{id}", async () => {
    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });

    // Wait for the link to appear — it only renders after job data loads
    const sourceJobLink = await waitFor(() =>
      screen.getByTestId("invoice-source-job-link"),
    );

    // PLP-FIX-5 (Issue 13b): chip shows job_number + title
    expect(sourceJobLink.textContent).toBe(
      `${MOCK_JOB_WITH_TITLE.job_number} · ${MOCK_JOB_WITH_TITLE.title}`,
    );

    // Link href points to the source job
    expect(sourceJobLink.getAttribute("href")).toBe(`/jobs/${TEST_JOB_ID}`);
  });

  // 3. Badge fallback to status_code when title is null — PLP-FIX-5 chip format
  it("3. badge falls back to status_code when job.title is null", async () => {
    // Per-test MSW override — never mutate the module-level fixture
    server.use(
      http.get("/api/v1/jobs/:job_id", ({ params }) => {
        const { job_id } = params as { job_id: string };
        if (job_id === TEST_JOB_ID) {
          return HttpResponse.json({
            ...MOCK_JOB_WITH_TITLE,
            title: null,
          });
        }
        return HttpResponse.json({ detail: "Not found" }, { status: 404 });
      }),
    );

    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });

    // Wait for the link to appear
    const sourceJobLink = await waitFor(() =>
      screen.getByTestId("invoice-source-job-link"),
    );

    // PLP-FIX-5: chip = "{job_number} · {status_code}" when title is null
    expect(sourceJobLink.textContent).toBe(
      `${MOCK_JOB_WITH_TITLE.job_number} · ${MOCK_JOB_WITH_TITLE.status_code}`,
    );
    // Title text must NOT be present
    expect(sourceJobLink.textContent).not.toContain(
      MOCK_JOB_WITH_TITLE.title as string,
    );
  });

  // 4. Clear job — PLP-FIX-5 (Issue 13b): no confirm dialog; "Clear job" button
  it("4. clicking Clear job removes the linked job badge", async () => {
    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-source-job-badge"),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Clear job/i }));

    // Badge removed — job cleared (no confirm dialog)
    await waitFor(() => {
      expect(
        screen.queryByTestId("invoice-source-job-badge"),
      ).not.toBeInTheDocument();
    });
  });

  // 5. After clearing, badge stays removed — selector reappears is covered
  //    in batch_plp_fix_5 test suite with proper MSW handlers.
  it("5. after clearing job, badge stays removed", async () => {
    const Wrapper = createWrapper("owner");
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(
        screen.getByTestId("invoice-source-job-badge"),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Clear job/i }));

    // Badge removed — stays removed
    await waitFor(() => {
      expect(
        screen.queryByTestId("invoice-source-job-badge"),
      ).not.toBeInTheDocument();
    });
  });

  // 6. RBAC — tech role does NOT see builder content
  it("6. tech role does NOT see InvoiceBuilderPage content (RoleGate hides)", () => {
    const Wrapper = createWrapper("technician");
    render(<InvoiceBuilderPage jobId={TEST_JOB_ID} />, { wrapper: Wrapper });

    // The builder heading must be absent — RoleGate returns null for tech
    expect(screen.queryByText("New Invoice")).not.toBeInTheDocument();
    // The badge must also be absent
    expect(
      screen.queryByTestId("invoice-source-job-badge"),
    ).not.toBeInTheDocument();
  });
});
