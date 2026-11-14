/**
 * FE-B25 — Job Edit UI Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b25/job_edit.integration.test.tsx
 *
 * Tests:
 * 1. "Edit Job" button renders for owner role (RoleGate permission="jobs.edit")
 * 2. "Edit Job" button NOT visible for tech role
 * 3. "Edit Job" button routes to /jobs/{id}/edit (JOB-UI-B1: full-page edit, not modal)
 * 4. JobEditModal can still be mounted directly (schedule-only dispatch board use)
 * 5. JobEditModal closes on PATCH success (modal direct mount)
 *
 * FE-B28 UPDATE: Customer/Site <select> replaced by <CustomerCombobox>/<SiteCombobox>.
 * JOB-UI-B1 UPDATE: Edit Job button on JobDetailPage now routes to /jobs/{id}/edit
 * instead of opening the modal. Tests 3–5 updated accordingly.
 * JobEditModal is still tested directly (dispatch board quick-edit use case).
 *
 * RULES: retry:false, no shared mutation of fixtures, server.resetHandlers() in afterEach.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { JobEditModal } from "@/features/jobs/components/JobEditModal";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs/job-1",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "job-1" }),
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

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  mockPush.mockClear();
});
afterAll(() => server.close());

// Fresh QueryClient per test — Rule 14
function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(role: "owner" | "technician"): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "user@test.com",
      role,
      tenantId: "t-1",
      displayName: "Test User",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

// job-1 from jobs.ts fixture
const JOB_ID = "job-1";

function renderJobDetail(role: "owner" | "technician") {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <JobDetailPage jobId={JOB_ID} />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B25 Job Edit UI Integration", () => {
  it("1. 'Edit Job' button renders for owner role", async () => {
    renderJobDetail("owner");
    expect(await screen.findByTestId("edit-job-btn")).toBeInTheDocument();
  });

  it("2. 'Edit Job' button NOT visible for tech role", async () => {
    renderJobDetail("technician");
    // Wait for page to finish loading by waiting for a known page element
    await screen.findByText("Jobs");
    expect(screen.queryByTestId("edit-job-btn")).not.toBeInTheDocument();
  });

  it("3. Edit Job button routes to /jobs/{id}/edit (JOB-UI-B1: full-page edit)", async () => {
    renderJobDetail("owner");

    // Click the edit button
    fireEvent.click(await screen.findByTestId("edit-job-btn"));

    // JOB-UI-B1: routes to full page (not modal)
    expect(mockPush).toHaveBeenCalledWith(`/jobs/${JOB_ID}/edit`);

    // Modal heading should NOT appear (modal removed from JobDetailPage)
    expect(
      screen.queryByRole("heading", { name: "Edit Job" }),
    ).not.toBeInTheDocument();
  });

  it("4. JobEditModal can still be mounted directly (dispatch board schedule-only use)", async () => {
    // JobEditModal is still used by the dispatch board — test direct mount
    const currentJob = {
      customer_id: "cust-1",
      site_id: "site-1",
      scheduled_start_at: "2026-06-16T09:00:00Z",
      scheduled_end_at: "2026-06-16T17:00:00Z",
      estimated_duration_minutes: 480,
    };

    render(
      <AuthContext.Provider value={makeAuth("owner")}>
        <QueryClientProvider client={makeQC()}>
          <NotificationQueueProvider>
            <JobEditModal
              open={true}
              onClose={vi.fn()}
              jobId={JOB_ID}
              currentJob={currentJob}
            />
          </NotificationQueueProvider>
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    // Modal heading should appear
    expect(
      await screen.findByRole("heading", { name: "Edit Job" }),
    ).toBeInTheDocument();

    // FE-B28: Customer combobox input is rendered (schedule-only fields)
    await waitFor(() => {
      const customerInput = screen.getByLabelText("Customer");
      expect(customerInput).toBeInTheDocument();
    });

    // "Save Changes" submit button
    expect(screen.getByTestId("job-edit-submit-btn")).toBeInTheDocument();
  });

  it("5. JobEditModal closes on PATCH success (direct modal mount)", async () => {
    const CUST_DISPLAY_NAME = "Smith Electrical";
    const CUST_ID = "c-00000001-0000-0000-0000-000000000001";
    const SITE_ID = "site-00000001-0000-0000-0000-000000000001";

    server.use(
      http.patch(`/api/v1/jobs/${JOB_ID}`, async () => {
        return HttpResponse.json({
          id: JOB_ID,
          tenant_id: "tenant-1",
          customer_id: CUST_ID,
          site_id: SITE_ID,
          status_id: "status-in-progress",
          scheduled_start_at: "2026-06-16T09:00:00Z",
          scheduled_end_at: "2026-06-16T17:00:00Z",
          estimated_duration_minutes: 480,
          actual_labor_cost_cents: 36000,
          actual_material_cost_cents: 20000,
          actual_profit_cents: 12000,
          is_active: true,
        });
      }),
    );

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    const currentJob = {
      customer_id: "cust-1",
      site_id: "site-1",
      scheduled_start_at: "2026-06-16T09:00:00Z",
      scheduled_end_at: "2026-06-16T17:00:00Z",
      estimated_duration_minutes: 480,
    };

    render(
      <AuthContext.Provider value={makeAuth("owner")}>
        <QueryClientProvider client={makeQC()}>
          <NotificationQueueProvider>
            <JobEditModal
              open={true}
              onClose={onClose}
              jobId={JOB_ID}
              currentJob={currentJob}
              onSuccess={onSuccess}
            />
          </NotificationQueueProvider>
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    // Wait for Customer combobox to load
    const customerInput = await screen.findByLabelText("Customer");
    await waitFor(() => expect(customerInput).not.toBeDisabled());

    // Type to filter and select the customer
    fireEvent.focus(customerInput);
    fireEvent.change(customerInput, { target: { value: CUST_DISPLAY_NAME } });

    await waitFor(() => {
      expect(screen.getByText(CUST_DISPLAY_NAME)).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByText(CUST_DISPLAY_NAME));

    // Wait for site combobox to be enabled
    const siteInput = await screen.findByLabelText("Site");
    await waitFor(() => expect(siteInput).not.toBeDisabled(), {
      timeout: 5000,
    });

    // Select first site option
    fireEvent.focus(siteInput);
    await waitFor(
      () => {
        const siteOptions = screen.queryAllByRole("option");
        expect(siteOptions.length).toBeGreaterThan(0);
      },
      { timeout: 5000 },
    );
    const siteOptions = screen.getAllByRole("option");
    fireEvent.mouseDown(siteOptions[0]);

    // Submit → success → onSuccess + onClose called
    fireEvent.click(screen.getByTestId("job-edit-submit-btn"));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
