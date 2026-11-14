/**
 * FE-B31 Integration — JobFormModal Recurrence Toggle
 *
 * Location: apps/web/src/__tests__/batch_fe_b31/job_form_recurrence_toggle.integration.test.tsx
 *
 * Tests:
 * 1. Recurrence config section NOT visible initially (toggle unchecked by default)
 * 2. Checking the toggle makes recurrence config section visible
 * 3. With toggle on + fields filled → POST to /api/v1/job-recurrence-rules/ (not /api/v1/jobs/)
 * 4. Submit without starts_on → form validation prevents POST
 *
 * Rules: Rule 14 (retry: false), MSW resetHandlers in afterEach.
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
  render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <JobsPage />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );

  // Click "Add Job" to open modal
  const addBtn = await screen.findByTestId("add-job-btn");
  fireEvent.click(addBtn);

  // Wait for modal to appear
  await screen.findByRole("dialog");
}

describe("FE-B31 JobFormModal Recurrence Toggle Integration", () => {
  it("1. recurrence config section NOT visible by default", async () => {
    await openJobFormModal();

    // Toggle checkbox should be unchecked
    const toggle = screen.getByTestId("recurrence-toggle");
    expect(toggle).not.toBeChecked();

    // Recurrence config section should not be in DOM
    expect(screen.queryByTestId("recurrence-config")).not.toBeInTheDocument();
  });

  it("2. checking toggle makes recurrence config visible", async () => {
    await openJobFormModal();

    const toggle = screen.getByTestId("recurrence-toggle");
    fireEvent.click(toggle);

    // Recurrence config should now be visible
    await waitFor(() => {
      expect(screen.getByTestId("recurrence-config")).toBeInTheDocument();
    });

    // Pattern dropdown, interval input, and starts-on date input should appear
    expect(screen.getByTestId("recurrence-pattern")).toBeInTheDocument();
    expect(screen.getByTestId("recurrence-interval")).toBeInTheDocument();
    expect(screen.getByTestId("recurrence-starts-on")).toBeInTheDocument();
  });

  it("3. with toggle on + starts_on filled → POST to /api/v1/job-recurrence-rules/", async () => {
    const CUST_DISPLAY_NAME = "Smith Electrical";
    const CUST_ID = "c-00000001-0000-0000-0000-000000000001";

    let rulePostBody: Record<string, unknown> | null = null;
    let jobsPostCalled = false;

    server.use(
      http.post("/api/v1/job-recurrence-rules/", async ({ request }) => {
        rulePostBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "rule-new-test",
            tenant_id: "t-1",
            customer_id: rulePostBody.customer_id,
            site_id: rulePostBody.site_id,
            pattern: rulePostBody.pattern ?? "weekly",
            interval_count: 1,
            starts_on: rulePostBody.starts_on,
            ends_on: null,
            max_occurrences: null,
            occurrences_created: 1,
            next_job_at: null,
            is_active: true,
            first_job_id: "job-new-test",
          },
          { status: 201 },
        );
      }),
      http.post("/api/v1/jobs/", async () => {
        jobsPostCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    await openJobFormModal();

    // Enable recurrence toggle
    const toggle = screen.getByTestId("recurrence-toggle");
    fireEvent.click(toggle);
    await screen.findByTestId("recurrence-config");

    // Fill customer combobox
    const customerInput = await screen.findByLabelText("Customer");
    await waitFor(() => expect(customerInput).not.toBeDisabled());
    fireEvent.focus(customerInput);
    fireEvent.change(customerInput, { target: { value: CUST_DISPLAY_NAME } });
    await waitFor(() => {
      expect(screen.getByText(CUST_DISPLAY_NAME)).toBeInTheDocument();
    });
    fireEvent.mouseDown(screen.getByText(CUST_DISPLAY_NAME));

    // Fill site combobox
    const siteInput = await screen.findByLabelText("Site");
    await waitFor(() => expect(siteInput).not.toBeDisabled(), {
      timeout: 5000,
    });
    fireEvent.focus(siteInput);
    await waitFor(
      () => {
        const opts = screen.queryAllByRole("option");
        expect(opts.length).toBeGreaterThan(0);
      },
      { timeout: 5000 },
    );
    fireEvent.mouseDown(screen.getAllByRole("option")[0]);

    // Fill starts_on
    const startsOnInput = screen.getByTestId("recurrence-starts-on");
    fireEvent.change(startsOnInput, { target: { value: "2026-08-01" } });

    // Submit
    fireEvent.click(screen.getByTestId("job-submit-btn"));

    await waitFor(() => {
      expect(rulePostBody).not.toBeNull();
      expect(rulePostBody?.customer_id).toBe(CUST_ID);
      expect(rulePostBody?.starts_on).toBe("2026-08-01");
      expect(jobsPostCalled).toBe(false); // jobs/ NOT called
    });
  });

  it("4. submit without starts_on shows validation error (does not POST)", async () => {
    let rulePostCalled = false;

    server.use(
      http.post("/api/v1/job-recurrence-rules/", async () => {
        rulePostCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    await openJobFormModal();

    // Enable recurrence
    fireEvent.click(screen.getByTestId("recurrence-toggle"));
    await screen.findByTestId("recurrence-config");

    // Do NOT fill starts_on — attempt submit directly
    fireEvent.click(screen.getByTestId("job-submit-btn"));

    // The form-level or app-level validation should block the POST.
    // We expect rulePostCalled to remain false after a brief wait.
    await new Promise((r) => setTimeout(r, 300));
    expect(rulePostCalled).toBe(false);
  });
});
