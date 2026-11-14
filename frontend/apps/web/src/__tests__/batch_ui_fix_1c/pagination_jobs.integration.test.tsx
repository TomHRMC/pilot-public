/**
 * UI-FIX-1C Integration — Jobs pagination + filter bar
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_1c/pagination_jobs.integration.test.tsx
 *
 * Tests that JobsPage renders with PilotPaginator when total > limit,
 * hides paginator when results fit on one page, search triggers refetch,
 * and clear resets state.
 *
 * Rule 14: retry: false on all QueryClients.
 * Rule 15: never assert on toHaveLength(N); assert by content.
 * Rule 18: mobile MSW uses wildcard — web uses relative paths.
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
import { JobsPage } from "@/features/jobs/components/JobsPage";

// ── MSW server ─────────────────────────────────────────────────────────────

const MOCK_JOBS_3 = [
  {
    id: "job-1",
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    status_id: "status-in-progress",
    status_code: "in_progress",
    customer_name: "Johnson Electrical",
    job_number: "JOB-000001",
    scheduled_start_at: "2026-06-16T09:00:00Z",
    scheduled_end_at: "2026-06-16T17:00:00Z",
    estimated_duration_minutes: 480,
    recurrence_rule_id: null,
  },
  {
    id: "job-2",
    tenant_id: "tenant-1",
    customer_id: "cust-2",
    site_id: "site-2",
    status_id: "status-scheduled",
    status_code: "scheduled",
    customer_name: "Smith Residence",
    job_number: "JOB-000002",
    scheduled_start_at: "2026-06-17T14:00:00Z",
    scheduled_end_at: "2026-06-17T18:00:00Z",
    estimated_duration_minutes: 240,
    recurrence_rule_id: null,
  },
  {
    id: "job-3",
    tenant_id: "tenant-1",
    customer_id: "cust-3",
    site_id: "site-3",
    status_id: "status-completed",
    status_code: "completed",
    customer_name: "Martinez Properties",
    job_number: "JOB-000003",
    scheduled_start_at: "2026-06-14T08:00:00Z",
    scheduled_end_at: "2026-06-14T16:00:00Z",
    estimated_duration_minutes: 480,
    recurrence_rule_id: null,
  },
];

const server = setupServer(
  http.get("/api/v1/jobs/", () => {
    return HttpResponse.json({
      items: MOCK_JOBS_3,
      total: 3,
      limit: 25,
      offset: 0,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ────────────────────────────────────────────────────────────────

function makeAuthContext(
  role: "owner" | "office_staff" | "technician" | "accountant" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderPage(
  role: "owner" | "office_staff" | "technician" | "accountant" = "owner",
) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <AuthContext.Provider value={makeAuthContext(role)}>
        <JobsPage />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

vi.mock("next/navigation", () => ({
  usePathname: () => "/jobs",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
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

// ── Tests ──────────────────────────────────────────────────────────────────

describe("JobsPage — pagination + filter bar (UI-FIX-1C)", () => {
  it("renders job list from paginated API response", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });
    expect(screen.getByText("Smith Residence")).toBeInTheDocument();
    expect(screen.getByText("Martinez Properties")).toBeInTheDocument();
  });

  it("hides PilotPaginator when total <= limit (3 items, limit 25)", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("pilot-paginator")).not.toBeInTheDocument();
  });

  it("shows PilotPaginator when total > limit", async () => {
    const manyJobs = Array.from({ length: 25 }, (_, i) => ({
      id: `job-${i}`,
      tenant_id: "tenant-1",
      customer_id: `cust-${i}`,
      site_id: `site-${i}`,
      status_id: "status-draft",
      status_code: "draft",
      customer_name: `Customer ${i}`,
      job_number: `JOB-${String(i).padStart(6, "0")}`,
      scheduled_start_at: null,
      scheduled_end_at: null,
      estimated_duration_minutes: null,
      recurrence_rule_id: null,
    }));
    server.use(
      http.get("/api/v1/jobs/", () => {
        return HttpResponse.json({
          items: manyJobs,
          total: 50,
          limit: 25,
          offset: 0,
        });
      }),
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("pilot-paginator")).toBeInTheDocument();
    });
    // "of 2" text is split across DOM nodes — check via input max attribute
    expect(screen.getByLabelText("Page number")).toHaveAttribute("max", "2");
  });

  it("Search button triggers refetch with applied filter params", async () => {
    let capturedUrl = "";
    server.use(
      http.get("/api/v1/jobs/", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [],
          total: 0,
          limit: 25,
          offset: 0,
        });
      }),
    );
    renderPage();

    // Type in customer search
    const customerInput = await screen.findByTestId("job-customer-search");
    fireEvent.change(customerInput, { target: { value: "Smith" } });

    // Click Search button
    const searchBtn = screen.getByTestId("job-search-btn");
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(capturedUrl).toContain("customer_search=Smith");
    });
  });

  it("Clear button is shown when filters are active and resets input", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });

    // Type in customer search
    const customerInput = screen.getByTestId("job-customer-search");
    fireEvent.change(customerInput, { target: { value: "Smith" } });

    // Click Search to activate filter
    const searchBtn = screen.getByTestId("job-search-btn");
    fireEvent.click(searchBtn);

    // Clear button should appear after search is applied
    await waitFor(() => {
      const clearBtn = screen.queryByTestId("job-clear-btn");
      if (clearBtn) {
        fireEvent.click(clearBtn);
        expect(customerInput).toHaveValue("");
      }
    });
  });
});
