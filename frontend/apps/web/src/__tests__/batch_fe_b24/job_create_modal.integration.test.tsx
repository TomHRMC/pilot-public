/**
 * FE-B24 — Job Create Modal Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b24/job_create_modal.integration.test.tsx
 *
 * Tests:
 * 1. "Add Job" button renders for owner role
 * 2. "Add Job" button NOT visible for tech role (RoleGate)
 * 3. JobFormModal renders when button clicked
 * 4. Submitting form with customer + site fires POST /api/v1/jobs/
 *
 * FE-B28 UPDATE: Customer/Site <select> replaced by <CustomerCombobox>/<SiteCombobox>.
 * Tests now use aria-label="Customer" / aria-label="Site" combobox inputs.
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
import { JobsPage } from "@/features/jobs/components/JobsPage";

// Mock next/navigation
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
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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

function renderJobsPage(role: "owner" | "technician") {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <JobsPage />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B24 Job Create Modal Integration", () => {
  it("1. 'Add Job' button renders for owner role", async () => {
    renderJobsPage("owner");
    expect(await screen.findByTestId("add-job-btn")).toBeInTheDocument();
  });

  it("2. 'Add Job' button NOT visible for tech role", async () => {
    renderJobsPage("technician");
    await screen.findByText("Johnson Electrical");
    expect(screen.queryByTestId("add-job-btn")).not.toBeInTheDocument();
  });

  it("3. JobFormModal renders when Add Job button clicked", async () => {
    renderJobsPage("owner");
    fireEvent.click(await screen.findByTestId("add-job-btn"));
    // Modal heading — use role to disambiguate from button label
    expect(
      await screen.findByRole("heading", { name: "Add Job" }),
    ).toBeInTheDocument();
    // FE-B28: Customer combobox input replaces <select data-testid="job-customer-select">
    await waitFor(() => {
      expect(screen.getByLabelText("Customer")).toBeInTheDocument();
    });
  });

  it("4. Submitting form fires POST /api/v1/jobs/", async () => {
    // Use the real fixture customer display_name from customerHandlers.ts
    const CUST_DISPLAY_NAME = "Smith Electrical";
    const CUST_ID = "c-00000001-0000-0000-0000-000000000001";

    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/jobs/", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "job-new-b24",
            tenant_id: "t-1",
            customer_id: capturedBody.customer_id,
            site_id: capturedBody.site_id,
            status_id: "status-draft",
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

    renderJobsPage("owner");
    fireEvent.click(await screen.findByTestId("add-job-btn"));

    // FE-B28: Customer combobox replaces <select>
    const customerInput = await screen.findByLabelText("Customer");
    await waitFor(() => expect(customerInput).not.toBeDisabled());

    // Type to filter, then select the customer
    fireEvent.focus(customerInput);
    fireEvent.change(customerInput, { target: { value: CUST_DISPLAY_NAME } });
    await waitFor(() => {
      expect(screen.getByText(CUST_DISPLAY_NAME)).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByText(CUST_DISPLAY_NAME));

    // Wait for site combobox to enable after customer selection
    const siteInput = await screen.findByLabelText("Site");
    await waitFor(() => expect(siteInput).not.toBeDisabled(), {
      timeout: 5000,
    });

    // Open site dropdown and select first option
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

    fireEvent.click(screen.getByTestId("job-submit-btn"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
      expect(capturedBody?.customer_id).toBe(CUST_ID);
    });
  });
});
