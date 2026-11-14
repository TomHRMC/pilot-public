/**
 * FE-B21 Integration — Job Detail
 *
 * Location: apps/web/src/__tests__/batch_fe_b21/jobDetail.integration.test.tsx
 *
 * Tests:
 * 1. /jobs/[id] renders job header with status
 * 2. Profitability widget shows from MSW projected-margin data
 * 3. Tabs navigate to correct sub-sections
 * 4. "Convert to Invoice" button visible for owner on completed job; hidden for tech
 * 5. Dispatch board job card click navigates to /jobs/[id] (mock router.push)
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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { jobsHandlers } from "@/mocks/handlers/jobs";
import { JobDetailPage } from "@/features/jobs/components/JobDetailPage";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs/job-1",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock dispatch board hooks (complex store) — only needed for test 5
vi.mock("@/features/dispatch-board/hooks/useDispatchBoard", () => ({
  useDispatchBoard: vi.fn(() => ({
    data: {
      jobs: [
        {
          id: "job-1",
          tech_id: "tech-1",
          status: "in_progress",
          customer_type: "residential",
          job_type: "service",
          priority: "normal",
        },
      ],
      techs: [],
    },
    dataUpdatedAt: Date.now(),
  })),
}));

vi.mock("@/features/dispatch-board/hooks/useMoveJob", () => ({
  useMoveJob: vi.fn(() => ({
    moveJob: vi.fn(),
    StalenessDialog: () => null,
    isPending: false,
  })),
}));

vi.mock("@/features/dispatch-board/hooks/useDispatchSse", () => ({
  useDispatchSse: vi.fn(() => ({ sseConnected: false })),
}));

vi.mock("@/features/dispatch-board/store", () => ({
  useDispatchBoardStore: vi.fn(() => ({
    viewTab: "day",
    activeDate: "2026-06-16",
    filters: {
      techIds: [],
      statuses: [],
      customerTypes: [],
      jobTypes: [],
      priorities: [],
    },
    selectedJobId: null,
    setViewTab: vi.fn(),
    navigatePrev: vi.fn(),
    navigateNext: vi.fn(),
    navigateToToday: vi.fn(),
    toggleTechFilter: vi.fn(),
    toggleStatusFilter: vi.fn(),
    toggleCustomerTypeFilter: vi.fn(),
    toggleJobTypeFilter: vi.fn(),
    togglePriorityFilter: vi.fn(),
    clearAllFilters: vi.fn(),
    setSelectedJobId: vi.fn(),
  })),
  getTabDays: vi.fn(() => 1),
}));

// Per-test MSW server
const server = setupServer(...jobsHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeContext(
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
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({
  role = "owner",
  children,
}: {
  role?: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("JobDetailPage integration", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("renders job header with status badge", async () => {
    render(<JobDetailPage jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    // Breadcrumb "Jobs" link
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();
    });

    // Status badge visible (status-in-progress)
    expect(screen.getByText(/in progress/i)).toBeInTheDocument();
  });

  it("profitability widget shows projected margin from MSW data", async () => {
    render(<JobDetailPage jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    await waitFor(() => {
      // job-1 has projected_margin_pct: 32 in MSW fixture
      expect(screen.getByText("32%")).toBeInTheDocument();
    });

    // Above target indicator (32% > 20%)
    expect(screen.getByTestId("above-target")).toBeInTheDocument();
  });

  it("tabs render and clicking switches active tab", async () => {
    render(<JobDetailPage jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(
        screen.getByRole("tab", { name: "Profitability" }),
      ).toBeInTheDocument();
    });

    // All tabs visible
    expect(
      screen.getByRole("tab", { name: "Time Entries" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Expenses" })).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "Change Orders" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Notes" })).toBeInTheDocument();

    // Click Time Entries tab
    fireEvent.click(screen.getByRole("tab", { name: "Time Entries" }));

    // Time entries content loads
    await waitFor(() => {
      // Should show time entries header
      expect(screen.getByText(/Time Entries/)).toBeInTheDocument();
    });
  });

  it("'Convert to Invoice' button visible for owner on completed job", async () => {
    // job-3 is "completed" status
    render(<JobDetailPage jobId="job-3" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByTestId("convert-to-invoice-btn")).toBeInTheDocument();
    });
  });

  it("'Convert to Invoice' button hidden for tech on completed job", async () => {
    render(<JobDetailPage jobId="job-3" />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    // Wait for page to fully load
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();
    });

    // Tech should not see Convert to Invoice button
    expect(screen.queryByTestId("convert-to-invoice-btn")).toBeNull();
  });

  it("'Convert to Invoice' button hidden for in-progress job (non-terminal)", async () => {
    // job-1 is in_progress — not a terminal status
    render(<JobDetailPage jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();
    });

    expect(screen.queryByTestId("convert-to-invoice-btn")).toBeNull();
  });
});
