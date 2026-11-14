/**
 * DispatchBoardPage — Integration Tests (BETA-B5 multi-day views)
 *
 * Location: apps/web/__tests__/batch_beta_b5/DispatchBoardPage.integration.test.tsx
 * Per batch-beta-v1-fixes-b5-design.md §I.2
 *
 * Scenarios:
 * 1. Tab switch to 4-Day → MultiDayGrid renders
 * 2. Tab switch to Week → MultiDayGrid renders with 7 date panels
 * 3. Tab switch to Month → MonthDeferredState renders (no grid)
 * 4. Tab switch back to Day → Day view renders (not MultiDayGrid)
 * 5. 4-Day grid: 4 date panel headers with consecutive dates
 * 6. Navigate prev/next in 4-Day: activeDate advances by 4
 * 7. API called with correct date range when tab switches
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
import { handlers } from "../../src/mocks/handlers";
import {
  useDispatchBoardStore,
  getTabDays,
} from "../../src/features/dispatch-board/store";

// ── Auth mock ─────────────────────────────────────────────────────────────────
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

// Mock react-dnd HTML5 backend (no real pointer events in jsdom)
vi.mock("react-dnd", () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useDrag: () => [{ isDragging: false }, vi.fn(), vi.fn()],
  useDrop: () => [{ isOver: false, canDrop: true }, vi.fn()],
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  // Reset Zustand store to Day view between tests
  useDispatchBoardStore.setState({
    viewTab: "day",
    activeDate: "2026-06-10",
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

describe("DispatchBoardPage — Multi-Day View Integration (BETA-B5)", () => {
  it("switching to Week tab sets viewTab to 'week' (FE-B30: '4 Day' tab removed)", async () => {
    // FE-B30: "4 Day" tab no longer exists — replaced by test verifying Week tab works
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Week")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Week"));

    await waitFor(() => {
      expect(useDispatchBoardStore.getState().viewTab).toBe("week");
    });
  });

  it("switching to Week tab sets viewTab to 'week'", async () => {
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Week")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Week"));

    await waitFor(() => {
      expect(useDispatchBoardStore.getState().viewTab).toBe("week");
    });
  });

  it("switching to Month tab renders the calendar grid (not 'Month view coming soon')", async () => {
    // Set store directly to month view
    useDispatchBoardStore.setState({ viewTab: "month" });

    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    // BETA-B7: MonthCalendarGrid replaces MonthDeferredState — "coming soon" no longer shown
    await waitFor(() => {
      expect(
        screen.queryByText("Month view coming soon"),
      ).not.toBeInTheDocument();
    });

    // Calendar grid day headers should be visible instead
    await waitFor(() => {
      expect(screen.getByText("Sun")).toBeInTheDocument();
    });
  });

  it("Day view renders (no MultiDayGrid) when viewTab is 'day'", async () => {
    // Store is already 'day' from beforeEach reset
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      // Day view renders the toolbar
      expect(screen.getByText("Today")).toBeInTheDocument();
    });

    // "Month view coming soon" should NOT be visible in day mode
    expect(
      screen.queryByText("Month view coming soon"),
    ).not.toBeInTheDocument();
  });

  it("endDate is activeDate+6 when Week tab is active", () => {
    // FE-B30: "4day" removed; week = 7 days → endDate = activeDate+6
    expect(getTabDays("week")).toBe(7);

    const activeDate = "2026-06-10";
    const d = new Date(activeDate + "T12:00:00");
    d.setDate(d.getDate() + getTabDays("week") - 1);
    const endDate = d.toISOString().slice(0, 10);
    expect(endDate).toBe("2026-06-16");
  });

  it("endDate is activeDate+6 when Week tab is active", () => {
    expect(getTabDays("week")).toBe(7);

    const activeDate = "2026-06-10";
    const d = new Date(activeDate + "T12:00:00");
    d.setDate(d.getDate() + getTabDays("week") - 1);
    const endDate = d.toISOString().slice(0, 10);
    expect(endDate).toBe("2026-06-16");
  });

  it("navigateNext in Week mode advances activeDate by 7 days", () => {
    // FE-B30: "4day" removed; replacing with week-mode navigation test
    useDispatchBoardStore.setState({
      viewTab: "week",
      activeDate: "2026-06-10",
    });

    useDispatchBoardStore.getState().navigateNext();
    expect(useDispatchBoardStore.getState().activeDate).toBe("2026-06-17");
  });
});
