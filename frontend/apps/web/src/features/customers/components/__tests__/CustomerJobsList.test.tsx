/**
 * CustomerJobsList unit tests — UI-FIX-2D
 *
 * Location: apps/web/src/features/customers/components/__tests__/CustomerJobsList.test.tsx
 *
 * Pattern: vi.mock the useJobs hook (same as CustomersPage pattern).
 * No apiClient calls — no auth token needed.
 * PLP-FIX-2: "+ New Job" is now a button opening JobFormModal (not an anchor).
 *   RoleGate requires AuthContext; JobFormModal is mocked to avoid hook deps.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { CustomerJobsList } from "../CustomerJobsList";

vi.mock("next/navigation", () => ({
  usePathname: () => "/customers/cust-1/jobs",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("../../../jobs/hooks/useJobs", () => ({
  useJobs: vi.fn(),
  JOBS_QUERY_KEY: (opts: object) => ["jobs", opts ?? {}],
}));

// PLP-FIX-2: mock JobFormModal to avoid its hook dependencies
vi.mock("../../../jobs/components/JobFormModal", () => ({
  JobFormModal: ({
    open,
    prefilledCustomerId,
  }: {
    open: boolean;
    prefilledCustomerId?: string;
  }) =>
    open
      ? React.createElement(
          "div",
          { "data-testid": "mock-job-form-modal" },
          `prefilledCustomerId=${prefilledCustomerId}`,
        )
      : null,
}));

import { useJobs } from "../../../jobs/hooks/useJobs";

// ── Auth helper ──────────────────────────────────────────────────────────────

function makeAuthValue(
  role: "owner" | "technician" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u-00000001",
      email: "test@pilot.example.com",
      role,
      tenantId: "t-00000001",
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

const MOCK_JOBS = [
  {
    id: "job-1",
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    status_id: "status-scheduled",
    status_code: "scheduled",
    customer_name: "Apex Commercial LLC",
    job_number: "JOB-000001",
    scheduled_start_at: "2026-07-24T09:00:00Z",
    scheduled_end_at: "2026-07-24T13:00:00Z",
    estimated_duration_minutes: 240,
    recurrence_rule_id: null,
  },
  {
    id: "job-2",
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    status_id: "status-completed",
    status_code: "completed",
    customer_name: "Apex Commercial LLC",
    job_number: "JOB-000003",
    scheduled_start_at: "2026-07-10T08:30:00Z",
    scheduled_end_at: "2026-07-10T14:30:00Z",
    estimated_duration_minutes: 360,
    recurrence_rule_id: null,
  },
];

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWithQueryClient(
  ui: React.ReactElement,
  role: "owner" | "technician" = "owner",
) {
  const queryClient = makeQueryClient();
  return render(
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

const CUST_ID = "cust-1";

describe("CustomerJobsList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders job rows from mocked hook data", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    expect(screen.getByText("JOB-000001")).toBeInTheDocument();
    expect(screen.getByText("JOB-000003")).toBeInTheDocument();
  });

  it("does NOT render customer search input", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    // Customer search input must not be present — locked to customerId
    expect(
      screen.queryByPlaceholderText(/search by customer/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/search by customer/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("job-customer-search")).not.toBeInTheDocument();
  });

  it("renders status filter dropdown", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    const statusSelect = screen.getByTestId("customer-jobs-status-select");
    expect(statusSelect).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "All" })).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Scheduled" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Completed" }),
    ).toBeInTheDocument();
  });

  it("+ New Job button opens JobFormModal with prefilled customer (PLP-FIX-2)", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    const newJobBtn = screen.getByTestId("customer-jobs-new-btn");
    // PLP-FIX-2: it's a button now, not an anchor — no href attribute
    expect(newJobBtn).not.toHaveAttribute("href");
    fireEvent.click(newJobBtn);
    expect(screen.getByTestId("mock-job-form-modal")).toBeInTheDocument();
    expect(screen.getByTestId("mock-job-form-modal").textContent).toContain(
      `prefilledCustomerId=${CUST_ID}`,
    );
  });

  it("+ New Job button is hidden for tech role (RoleGate — PLP-FIX-2)", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: MOCK_JOBS, total: 2, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(
      <CustomerJobsList customerId={CUST_ID} />,
      "technician",
    );
    expect(
      screen.queryByTestId("customer-jobs-new-btn"),
    ).not.toBeInTheDocument();
  });

  it("renders empty state when no jobs returned", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: { items: [], total: 0, limit: 25, offset: 0 },
      isLoading: false,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    expect(screen.getAllByText(/no jobs/i).length).toBeGreaterThan(0);
  });

  it("renders loading state", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    expect(screen.getAllByText(/loading jobs/i).length).toBeGreaterThan(0);
  });

  it("renders error state on failure", () => {
    vi.mocked(useJobs).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as never);

    renderWithQueryClient(<CustomerJobsList customerId={CUST_ID} />);
    expect(screen.getByText(/could not load jobs/i)).toBeInTheDocument();
  });
});
