/**
 * JOB-UI-B1 Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_job_ui_b1/job_ui_b1.integration.test.tsx
 *
 * Covers (per spec):
 * 1. JobsPage — Title column renders title when present
 * 2. JobsPage — Title column falls back to job_number when title is null
 * 3. JobsPage — row Edit action navigates to /jobs/{id}/edit (assert push called)
 * 4. useJobTypes — returns list shape from MSW
 * 5. JobEditPage — renders all fields pre-filled from useJob
 * 6. JobEditPage — priority <select> has Standard / Urgent / Emergency
 * 7. JobEditPage — job_type <select> populated from useJobTypes
 * 8. JobEditPage — submit fires PATCH with only changed fields
 * 9. JobEditPage — RBAC: tech role sees nothing (jobs.edit gate)
 * 10. JobEditPage — illegal status transition: MSW 422 → form shows detail message
 * 11. JobDetailPage — title in header
 * 12. JobDetailPage — priority chip renders
 * 13. JobDetailPage — job_type chip renders
 * 14. JobDetailPage — Edit button routes to full page (not modal open)
 *
 * RULES: retry:false, fresh QueryClient per test, server.resetHandlers() afterEach,
 *        no shared fixture mutation, assert by ID not total count.
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
  beforeEach,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { handlers } from "@/mocks/handlers";
import { JobsPage } from "@/features/jobs/components/JobsPage";
import { JobEditPage } from "@/features/jobs/components/JobEditPage";
import { JobDetailPage } from "@/features/jobs/components/JobDetailPage";
import { renderHook, waitFor as waitForHook } from "@testing-library/react";
import { useJobTypes } from "@/features/jobs/hooks/useJobTypes";

// ── Navigation mock ───────────────────────────────────────────────────────────

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
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

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  mockPush.mockClear();
});
afterAll(() => server.close());

// ── Test helpers ──────────────────────────────────────────────────────────────

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(
  role: "owner" | "technician" | "office_staff" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "test@pilot.example.com",
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

function Wrapper({
  role = "owner",
  children,
}: {
  role?: "owner" | "technician" | "office_staff";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}

// ── 1–3: JobsPage Title column + row Edit action ──────────────────────────────

describe("JOB-UI-B1: JobsPage Title column", () => {
  beforeEach(() => mockPush.mockClear());

  it("1. renders title when job has a title", async () => {
    render(
      <Wrapper>
        <JobsPage />
      </Wrapper>,
    );

    await waitFor(() => {
      // job-1 fixture has title "Panel Upgrade — Johnson HQ"
      expect(
        screen.getByText("Panel Upgrade — Johnson HQ"),
      ).toBeInTheDocument();
    });
  });

  it("2. falls back to job_number when title is null", async () => {
    render(
      <Wrapper>
        <JobsPage />
      </Wrapper>,
    );

    await waitFor(() => {
      // job-4 fixture has title=null, job_number="JOB-000004"
      expect(screen.getByText("JOB-000004")).toBeInTheDocument();
    });
  });

  it("3. row Edit action navigates to /jobs/{id}/edit", async () => {
    render(
      <Wrapper>
        <JobsPage />
      </Wrapper>,
    );

    // Wait for table to load
    await waitFor(() => {
      expect(screen.getByTestId("edit-job-row-btn-job-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("edit-job-row-btn-job-1"));

    expect(mockPush).toHaveBeenCalledWith("/jobs/job-1/edit");
  });
});

// ── 4: useJobTypes hook ───────────────────────────────────────────────────────

describe("JOB-UI-B1: useJobTypes hook", () => {
  it("4. returns list shape from MSW (≥3 types)", async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={makeQC()}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useJobTypes(), { wrapper });

    await waitForHook(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const types = result.current.data!;
    expect(types.length).toBeGreaterThanOrEqual(3);
    // Spot-check fixture shape
    expect(types[0]).toMatchObject({
      id: "jt-1",
      code: "service",
      label: "Service Call",
    });
    expect(types[1]).toMatchObject({
      id: "jt-2",
      code: "installation",
      label: "Installation",
    });
  });
});

// ── 5–10: JobEditPage ─────────────────────────────────────────────────────────

describe("JOB-UI-B1: JobEditPage", () => {
  it("5. renders all fields pre-filled from useJob (job-1)", async () => {
    render(
      <Wrapper>
        <JobEditPage jobId="job-1" />
      </Wrapper>,
    );

    // Title pre-filled
    await waitFor(() => {
      const titleInput = screen.getByTestId(
        "job-edit-title-input",
      ) as HTMLInputElement;
      expect(titleInput.value).toBe("Panel Upgrade — Johnson HQ");
    });

    // Status select present
    expect(screen.getByTestId("job-edit-status-select")).toBeInTheDocument();
  });

  it("6. priority <select> has Standard / Urgent / Emergency options", async () => {
    render(
      <Wrapper>
        <JobEditPage jobId="job-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      const prioritySelect = screen.getByTestId("job-edit-priority-select");
      expect(prioritySelect).toBeInTheDocument();
    });

    const prioritySelect = screen.getByTestId("job-edit-priority-select");
    const options = Array.from(prioritySelect.querySelectorAll("option")).map(
      (o) => o.textContent,
    );
    expect(options).toContain("Standard");
    expect(options).toContain("Urgent");
    expect(options).toContain("Emergency");
  });

  it("7. job_type <select> is populated from useJobTypes (≥3 options)", async () => {
    render(
      <Wrapper>
        <JobEditPage jobId="job-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      const typeSelect = screen.getByTestId("job-edit-job-type-select");
      // — None — + ≥3 types = at least 4 options
      const options = typeSelect.querySelectorAll("option");
      expect(options.length).toBeGreaterThanOrEqual(4);
    });

    const typeSelect = screen.getByTestId("job-edit-job-type-select");
    const labels = Array.from(typeSelect.querySelectorAll("option")).map(
      (o) => o.textContent,
    );
    expect(labels).toContain("Service Call");
    expect(labels).toContain("Installation");
    expect(labels).toContain("Inspection");
  });

  it("8. submit fires PATCH with only changed fields (title change)", async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.patch("/api/v1/jobs/job-1", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: "job-1",
          tenant_id: "tenant-1",
          customer_id: "cust-1",
          site_id: "site-1",
          status_id: "status-in-progress",
          status_code: "in_progress",
          title: capturedBody.title ?? "Panel Upgrade — Johnson HQ",
          priority: "urgent",
          job_type_id: "jt-1",
          job_number: "JOB-000001",
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

    render(
      <Wrapper>
        <JobEditPage jobId="job-1" />
      </Wrapper>,
    );

    // Wait for form to load
    const titleInput = await screen.findByTestId("job-edit-title-input");

    // Change only the title
    fireEvent.change(titleInput, { target: { value: "Updated Panel Title" } });

    // Submit
    fireEvent.click(screen.getByTestId("job-edit-page-submit-btn"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
      // Only title was changed — partial payload
      expect(capturedBody?.title).toBe("Updated Panel Title");
      // Fields that didn't change should NOT be in payload
      expect(capturedBody?.priority).toBeUndefined();
      expect(capturedBody?.customer_id).toBeUndefined();
    });

    // After success → router.push to /jobs/job-1
    expect(mockPush).toHaveBeenCalledWith("/jobs/job-1");
  });

  it("9. RBAC: tech role sees nothing (jobs.edit gate)", async () => {
    render(
      <Wrapper role="technician">
        <JobEditPage jobId="job-1" />
      </Wrapper>,
    );

    // Wait a moment — RoleGate should render nothing for tech
    await new Promise((r) => setTimeout(r, 100));

    // Form fields should not be visible for tech
    expect(
      screen.queryByTestId("job-edit-page-submit-btn"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("job-edit-title-input"),
    ).not.toBeInTheDocument();
  });

  it("10. illegal status transition: MSW 422 → form shows RFC 7807 detail", async () => {
    server.use(
      http.patch("/api/v1/jobs/job-3", async () => {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/invalid-status-transition",
            title: "Invalid Status Transition",
            status: 422,
            detail: "Cannot transition from completed to draft.",
          },
          { status: 422 },
        );
      }),
    );

    render(
      <Wrapper>
        <JobEditPage jobId="job-3" />
      </Wrapper>,
    );

    // Wait for form to load
    await screen.findByTestId("job-edit-page-submit-btn");

    // Change status to draft (illegal from completed)
    const statusSelect = screen.getByTestId("job-edit-status-select");
    fireEvent.change(statusSelect, { target: { value: "draft" } });

    // Submit
    fireEvent.click(screen.getByTestId("job-edit-page-submit-btn"));

    await waitFor(() => {
      const errorEl = screen.getByTestId("job-edit-error");
      expect(errorEl).toBeInTheDocument();
      expect(errorEl.textContent).toContain(
        "Cannot transition from completed to draft.",
      );
    });
  });
});

// ── 11–14: JobDetailPage title, chips, Edit routing ──────────────────────────

describe("JOB-UI-B1: JobDetailPage title + chips + Edit routing", () => {
  beforeEach(() => mockPush.mockClear());

  it("11. title appears in job detail header (job-1 has title)", async () => {
    render(
      <Wrapper>
        <JobDetailPage jobId="job-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      // job-1 fixture has title "Panel Upgrade — Johnson HQ"
      expect(screen.getByTestId("job-detail-header-title")).toBeInTheDocument();
      expect(screen.getByTestId("job-detail-header-title").textContent).toBe(
        "Panel Upgrade — Johnson HQ",
      );
    });
  });

  it("12. priority chip renders for job with priority (job-1 = urgent)", async () => {
    render(
      <Wrapper>
        <JobDetailPage jobId="job-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      const chip = screen.getByTestId("job-priority-chip");
      expect(chip).toBeInTheDocument();
      expect(chip.textContent).toBe("Urgent");
    });
  });

  it("13. job_type chip renders for job with job_type_label (job-1 = Service Call)", async () => {
    render(
      <Wrapper>
        <JobDetailPage jobId="job-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      const chip = screen.getByTestId("job-type-chip");
      expect(chip).toBeInTheDocument();
      expect(chip.textContent).toBe("Service Call");
    });
  });

  it("14. Edit button routes to /jobs/{id}/edit (not modal open)", async () => {
    render(
      <Wrapper>
        <JobDetailPage jobId="job-1" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("edit-job-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("edit-job-btn"));

    // Should push to full-page edit, NOT open modal
    expect(mockPush).toHaveBeenCalledWith("/jobs/job-1/edit");

    // Modal heading should NOT appear (modal removed from JobDetailPage)
    expect(
      screen.queryByRole("heading", { name: "Edit Job" }),
    ).not.toBeInTheDocument();
  });
});
