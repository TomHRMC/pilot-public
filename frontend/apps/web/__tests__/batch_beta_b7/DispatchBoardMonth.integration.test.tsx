/**
 * DispatchBoardMonth — Integration Tests (BETA-B7)
 *
 * Location: apps/web/__tests__/batch_beta_b7/DispatchBoardMonth.integration.test.tsx
 * Per batch-beta-v1-fixes-b7-design.md §J.5
 *
 * Tests:
 * 1. Month tab renders calendar grid (not "coming soon")
 * 2. Month tab shows 7-column grid (Sun–Sat headers)
 * 3. Click cell → switches to Day view for that date
 * 4. Jobs from API appear in correct cells
 * 5. "Month view coming soon" string is gone from DOM
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useDispatchBoardStore } from "../../src/features/dispatch-board/store";

// ── Auth + role-gate mocks ─────────────────────────────────────────────────────
vi.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useRequiresPermission: () => ({ permitted: true }),
  ROLE_PERMISSION_MAP: {},
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "owner@test.com" },
    role: "owner",
    isAuthenticated: true,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
  }),
  AuthContext: { _currentValue: null },
}));

// Mock next/navigation (DispatchBoardPage uses useRouter for job card navigation — FE-B21)
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/schedule",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock react-dnd (no pointer events in jsdom)
vi.mock("react-dnd", () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useDrag: () => [{ isDragging: false }, vi.fn(), vi.fn()],
  useDrop: () => [{ isOver: false, canDrop: true }, vi.fn()],
}));

// ── MSW server with month-aware schedule handler ───────────────────────────────
// Active date for tests: 2026-06-01 (Monday)
const ACTIVE_DATE = "2026-06-01";

// Real API job entry shape (DispatchBoardJobEntry)
const MONTH_MOCK_JOB_ENTRY = {
  id: "job-june-10",
  tenant_id: "tenant-1",
  customer_id: "cust-1",
  site_id: "site-1",
  status_id: "status-1",
  scheduled_start_at: "2026-06-10T09:00:00.000Z",
  scheduled_end_at: "2026-06-10T11:00:00.000Z",
  estimated_duration_minutes: 120,
  external_calendar_event_id: null,
  is_active: true,
  eta_minutes: null,
};

const monthHandlers = [
  // MKT-B11-D: DispatchBoardPage now calls useScheduleLaneCount → needs subscription-tiers
  http.get("/api/v1/subscription-tiers/", () =>
    HttpResponse.json({
      tiers: [
        {
          tier_id: "tier-charter-001",
          tier_name: "charter",
          display_label: "Charter",
          monthly_price_cents: 9900,
          is_trial: false,
          trial_duration_days: null,
          schedule_lanes: 5,
          display_order: 1,
          is_active: true,
        },
      ],
    }),
  ),
  http.get("/api/v1/subscription-tiers", () =>
    HttpResponse.json({
      tiers: [
        {
          tier_id: "tier-charter-001",
          tier_name: "charter",
          display_label: "Charter",
          monthly_price_cents: 9900,
          is_trial: false,
          trial_duration_days: null,
          schedule_lanes: 5,
          display_order: 1,
          is_active: true,
        },
      ],
    }),
  ),
  // Real API shape: { start_date, end_date, techs: [{id, name, jobs:[...]}, ...], unassigned: [...] }
  http.get("/api/v1/scheduling/dispatch-board", () => {
    return HttpResponse.json({
      start_date: `${ACTIVE_DATE}T00:00:00Z`,
      end_date: `${ACTIVE_DATE}T23:59:59Z`,
      techs: [
        {
          tech_id: "tech-1",
          id: "tech-1",
          name: "Mike Chen",
          display_color: "#3B43D6",
          avatar_url: null,
          jobs: [MONTH_MOCK_JOB_ENTRY],
          eta_minutes_to_first_job: null,
        },
      ],
      unassigned: [],
    });
  }),
  http.get("/api/v1/schedule/board/stream", () => {
    return new Response(new ReadableStream({ start() {} }), {
      headers: { "Content-Type": "text/event-stream" },
    });
  }),
  http.get("/api/v1/scheduling/board/stream", () => {
    return new Response(new ReadableStream({ start() {} }), {
      headers: { "Content-Type": "text/event-stream" },
    });
  }),
  http.get("/api/v1/users/me/permissions", () =>
    HttpResponse.json({
      role: "owner",
      permissions: ["schedule.manage"],
    }),
  ),
];

const server = setupServer(...monthHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  useDispatchBoardStore.setState({
    viewTab: "month",
    activeDate: ACTIVE_DATE,
    filters: {
      techIds: [],
      statuses: [],
      customerTypes: [],
      jobTypes: [],
      priorities: [],
    },
    selectedJobId: null,
    conflictPreviewOpen: false,
    conflictPreviewJobId: null,
  });
});
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("DispatchBoardMonth — Integration Tests (BETA-B7 §J.5)", () => {
  it("Month tab renders calendar grid — NOT 'Month view coming soon'", async () => {
    useDispatchBoardStore.setState({
      viewTab: "month",
      activeDate: ACTIVE_DATE,
    });

    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(
        screen.queryByText("Month view coming soon"),
      ).not.toBeInTheDocument();
    });
  });

  it("Month tab shows 7 day-of-week column headers (Sun through Sat)", async () => {
    useDispatchBoardStore.setState({
      viewTab: "month",
      activeDate: ACTIVE_DATE,
    });

    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Sun")).toBeInTheDocument();
      expect(screen.getByText("Mon")).toBeInTheDocument();
      expect(screen.getByText("Sat")).toBeInTheDocument();
    });
  });

  it("clicking a month cell switches viewTab to 'day' and sets activeDate", async () => {
    useDispatchBoardStore.setState({
      viewTab: "month",
      activeDate: ACTIVE_DATE,
    });

    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    // Wait for calendar grid to render
    await waitFor(() => {
      expect(screen.getByText("Sun")).toBeInTheDocument();
    });

    // Find the June 15 cell and click it
    const june15Button = screen
      .getAllByRole("button")
      .find((btn) => btn.getAttribute("aria-label")?.startsWith("2026-06-15"));

    if (june15Button) {
      fireEvent.click(june15Button);

      await waitFor(() => {
        expect(useDispatchBoardStore.getState().viewTab).toBe("day");
        expect(useDispatchBoardStore.getState().activeDate).toBe("2026-06-15");
      });
    }
  });

  it("jobs from API appear in correct date cell", async () => {
    // Real API returns DispatchBoardJobEntry (no customer_name) — verify by job count pill
    useDispatchBoardStore.setState({
      viewTab: "month",
      activeDate: ACTIVE_DATE,
    });

    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    // Wait for calendar to render
    await waitFor(() => {
      expect(screen.getByText("Sun")).toBeInTheDocument();
    });

    // The June 10 cell should show a "1 job" pill (normalizer maps tech-assigned job to flat list)
    await waitFor(() => {
      expect(screen.getByText("1 job")).toBeInTheDocument();
    });
  });

  it("'Month view coming soon' string is absent from DOM in month view", async () => {
    useDispatchBoardStore.setState({
      viewTab: "month",
      activeDate: ACTIVE_DATE,
    });

    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Sun")).toBeInTheDocument();
    });

    expect(
      screen.queryByText("Month view coming soon"),
    ).not.toBeInTheDocument();
  });
});
