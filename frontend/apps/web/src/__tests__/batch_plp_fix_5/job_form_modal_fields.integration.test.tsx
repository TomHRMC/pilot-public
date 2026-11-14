/**
 * PLP-FIX-5 Part B — JobFormModal Title + Job Type + Success Notification
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_5/job_form_modal_fields.integration.test.tsx
 *
 * Tests:
 * 1. Title input renders (non-recurrence path)
 * 2. Job Type select renders with "No type" default
 * 3. Title + job type submit through the payload (MSW capture)
 * 4. Empty job type omits job_type_id from the payload (sends null)
 * 5. Success notification contains the job number
 * 6. Title + Job Type hidden when recurrence toggle is on
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
import { handlers } from "../../mocks/handlers";
import { JobsPage } from "@/features/jobs/components/JobsPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

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

// Capture addNotification calls
const addNotificationSpy = vi.fn();
vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: addNotificationSpy,
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
  NotificationBanner: () => null,
  NotificationQueueProvider: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  addNotificationSpy.mockClear();
});
afterAll(() => server.close());

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t-1",
      displayName: "Test Owner",
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

async function openJobFormModal() {
  addNotificationSpy.mockClear();
  render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <JobsPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
  const addBtn = await screen.findByTestId("add-job-btn");
  fireEvent.click(addBtn);
  await screen.findByRole("dialog");
}

// Helper to fill customer + site (minimum required fields)
async function fillCustomerAndSite() {
  const customerInput = await screen.findByLabelText("Customer");
  await waitFor(() => expect(customerInput).not.toBeDisabled());
  fireEvent.focus(customerInput);
  fireEvent.change(customerInput, { target: { value: "Smith Electrical" } });
  await waitFor(() => {
    expect(screen.getByText("Smith Electrical")).toBeInTheDocument();
  });
  fireEvent.mouseDown(screen.getByText("Smith Electrical"));

  const siteInput = await screen.findByLabelText("Site");
  await waitFor(() => expect(siteInput).not.toBeDisabled(), {
    timeout: 5000,
  });
  fireEvent.focus(siteInput);
  await waitFor(
    () => {
      expect(screen.queryAllByRole("option").length).toBeGreaterThan(0);
    },
    { timeout: 5000 },
  );
  fireEvent.mouseDown(screen.getAllByRole("option")[0]);
}

describe("PLP-FIX-5 — JobFormModal Title + Job Type + Success Notification", () => {
  it("1. Title input renders on non-recurrence path", async () => {
    await openJobFormModal();
    expect(screen.getByTestId("job-title-input")).toBeInTheDocument();
  });

  it("2. Job Type select renders with 'No type' default", async () => {
    await openJobFormModal();
    const select = screen.getByTestId("job-type-select");
    expect(select).toBeInTheDocument();
    // First option is "No type" with empty value
    expect(select.querySelector("option")?.textContent).toBe("No type");
  });

  it("3. Title + job type submit through the payload", async () => {
    const CUST_ID = "c-00000001-0000-0000-0000-000000000001";

    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/jobs/", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "job-plp-fix-5-001",
            tenant_id: "t-1",
            customer_id: CUST_ID,
            site_id: "s-001",
            status_id: "st-draft",
            status_code: "draft",
            job_number: "J-0007",
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

    await openJobFormModal();

    // Fill title
    const titleInput = screen.getByTestId("job-title-input");
    fireEvent.change(titleInput, { target: { value: "Panel upgrade" } });

    await fillCustomerAndSite();

    // Select job type (second option — first is "No type")
    const jobTypeSelect = screen.getByTestId("job-type-select");
    const options = jobTypeSelect.querySelectorAll("option");
    const selectedTypeId = options.length > 1 ? options[1].value : null;
    if (selectedTypeId) {
      fireEvent.change(jobTypeSelect, { target: { value: selectedTypeId } });
    }

    fireEvent.click(screen.getByTestId("job-submit-btn"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
    });
    const body = capturedBody as unknown as Record<string, unknown>;
    expect(body?.title).toBe("Panel upgrade");
    if (selectedTypeId) {
      expect(body?.job_type_id).toBe(selectedTypeId);
    }
  });

  it("4. empty job type omits job_type_id (sends null)", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/jobs/", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "job-no-type-001",
            tenant_id: "t-1",
            customer_id: "c-1",
            site_id: "s-1",
            status_id: "st-draft",
            status_code: "draft",
            job_number: "J-0008",
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

    await openJobFormModal();

    await fillCustomerAndSite();

    // Leave job type as "No type" (default empty)
    fireEvent.click(screen.getByTestId("job-submit-btn"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
    });
    expect(
      (capturedBody as unknown as Record<string, unknown>)?.job_type_id,
    ).toBeNull();
  });

  it("5. success notification contains the job number", async () => {
    server.use(
      http.post("/api/v1/jobs/", async () => {
        return HttpResponse.json(
          {
            id: "job-notif-001",
            tenant_id: "t-1",
            customer_id: "c-1",
            site_id: "s-1",
            status_id: "st-scheduled",
            status_code: "scheduled",
            job_number: "J-0009",
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

    await openJobFormModal();

    await fillCustomerAndSite();

    fireEvent.click(screen.getByTestId("job-submit-btn"));

    // Success notification should contain the job number
    await waitFor(() => {
      expect(addNotificationSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: "success",
          title: expect.stringContaining("J-0009"),
        }),
      );
    });
  });

  it("6. Title + Job Type hidden when recurrence toggle is on", async () => {
    await openJobFormModal();

    // Toggle recurrence on
    fireEvent.click(screen.getByTestId("recurrence-toggle"));
    await screen.findByTestId("recurrence-config");

    // Title input should NOT be in DOM
    expect(screen.queryByTestId("job-title-input")).not.toBeInTheDocument();
    // Job type select should NOT be in DOM
    expect(screen.queryByTestId("job-type-select")).not.toBeInTheDocument();
  });
});
