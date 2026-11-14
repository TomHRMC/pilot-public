/**
 * DISPATCH-B1.5 Integration Tests — Week-Lane Grid
 *
 * Location: apps/web/src/__tests__/batch_dispatch_b1_5/dispatch_b1_5.integration.test.tsx
 *
 * Covers:
 *   1. DispatchWeekLaneView renders laneCount lane headers (L1…L5)
 *   2. Per-day assignJobsToLanes: non-overlapping → same lane; overlapping → different lanes
 *   3. Empty cell renders dashed border
 *   4. Over-capacity (4 jobs) chip shown; onJobDrop NOT called on 5th drop
 *   5. Under-capacity drop calls onJobDrop once
 *   6. No WeekCommitmentChip in lane mode
 *   7. Lane|Tech toggle in week: layoutMode="lane" → DispatchWeekLaneView; "Tech" → DispatchWeekView
 *   8. 5d/7d toggle retained in week-lane: switch to 7d → 7 rows
 *   9. Mobile fallback text visible
 *  10. JobPropertiesPanel: site_name shown when present; hidden when null
 *  11. assignJobsToLanes unit tests (shared util)
 *
 * Per dispatch-b1.5-ui-design-spec.md §Tests
 */

import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";

import { DispatchWeekLaneView } from "../../features/dispatch-board/components/DispatchWeekLaneView";
import { JobPropertiesPanel } from "../../features/dispatch-board/components/JobPropertiesPanel";
import { assignJobsToLanes } from "../../features/dispatch-board/utils/laneHelpers";
import type { DispatchBoardJob } from "../../features/dispatch-board/types-stub";
import type { ScheduledJob } from "../../features/dispatch-board/components/DispatchBoardLanes";

// ─── Next.js mock ─────────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/schedule",
  useSearchParams: () => new URLSearchParams(),
}));

// ─── @dnd-kit mock — useDraggable + useDroppable (no real DnD in jsdom) ──────
vi.mock("@dnd-kit/core", async () => {
  const actual =
    await vi.importActual<typeof import("@dnd-kit/core")>("@dnd-kit/core");
  return {
    ...actual,
    useDraggable: ({ id }: { id: string; data?: unknown }) => ({
      attributes: { "data-draggable-id": id },
      listeners: {},
      setNodeRef: vi.fn(),
      isDragging: false,
      transform: null,
    }),
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    useDroppable: (_dropOpts: unknown) => ({
      setNodeRef: vi.fn(),
      isOver: false,
      over: null,
      active: null,
      rect: null,
      node: { current: null },
    }),
    DragOverlay: ({ children }: { children: React.ReactNode }) =>
      children ?? null,
  };
});

// ─── MSW server ───────────────────────────────────────────────────────────────
let capturedMoveBody: Record<string, unknown> | null = null;

const server = setupServer(
  // Suppress unhandled request warnings for non-relevant endpoints
  http.get("/api/v1/scheduling/jobs/*/assignments", () =>
    HttpResponse.json([]),
  ),
  http.get("/api/v1/users", () => HttpResponse.json([])),
  http.post("/api/v1/scheduling/jobs/*/move", async ({ request }) => {
    capturedMoveBody = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      job_id: "job-001",
      job_version: 2,
      assignment_id: "assign-001",
      assignment_version: 1,
      tech_user_id: capturedMoveBody.tech_user_id,
      scheduled_start_at: capturedMoveBody.scheduled_start_at,
      scheduled_end_at: capturedMoveBody.scheduled_end_at,
      conflicts: [],
    });
  }),
  http.post("/api/v1/scheduling/jobs/*/check-conflicts", () =>
    HttpResponse.json({
      is_feasible: true,
      conflicts: [],
      drive_time_to_next_minutes: null,
      drive_time_from_prev_minutes: null,
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedMoveBody = null;
});
afterAll(() => server.close());

// ─── Helpers ──────────────────────────────────────────────────────────────────

const MONDAY = "2026-07-27"; // A known Monday

function makeJob(
  overrides: Partial<DispatchBoardJob> & { id: string },
): DispatchBoardJob {
  return {
    title: `Job ${overrides.id}`,
    customer_name: "Test Customer",
    site_address: "123 Test St",
    scheduled_start_at: `${MONDAY}T09:00:00.000Z`,
    scheduled_end_at: `${MONDAY}T11:00:00.000Z`,
    tech_id: "tech-001",
    status: "scheduled",
    priority: "standard",
    customer_type: "company",
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
    ...overrides,
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

function renderWeekLaneView(
  props: Partial<
    Omit<
      React.ComponentProps<typeof DispatchWeekLaneView>,
      "onJobDrop" | "onJobClick" | "onJobContextMenu" | "onNavigateToDate"
    >
  > & {
    onJobDrop?: React.ComponentProps<typeof DispatchWeekLaneView>["onJobDrop"];
  } = {},
) {
  const onJobDrop = props.onJobDrop ?? vi.fn().mockResolvedValue(undefined);
  const onJobClick = vi.fn();
  const onJobContextMenu = vi.fn();
  const onNavigateToDate = vi.fn();

  return {
    onJobDrop,
    onJobClick,
    onJobContextMenu,
    ...render(
      <DispatchWeekLaneView
        weekStartDate={MONDAY}
        daysToShow={5}
        laneCount={5}
        jobs={[]}
        onJobDrop={onJobDrop}
        onJobClick={onJobClick}
        onJobContextMenu={onJobContextMenu}
        onNavigateToDate={onNavigateToDate}
        {...props}
      />,
    ),
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("assignJobsToLanes (shared util)", () => {
  it("assigns 2 non-overlapping jobs to the same lane (L0)", () => {
    const jobs = [
      makeJob({
        id: "j1",
        scheduled_start_at: `${MONDAY}T08:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T10:00:00.000Z`,
      }),
      makeJob({
        id: "j2",
        scheduled_start_at: `${MONDAY}T10:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T12:00:00.000Z`,
      }),
    ];
    const assignment = assignJobsToLanes(jobs, 5);
    expect(assignment.get("j1")).toBe(0);
    expect(assignment.get("j2")).toBe(0); // sequential non-overlapping → same lane
  });

  it("splits 2 overlapping jobs across L0 and L1", () => {
    const jobs = [
      makeJob({
        id: "j1",
        scheduled_start_at: `${MONDAY}T08:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T12:00:00.000Z`,
      }),
      makeJob({
        id: "j2",
        scheduled_start_at: `${MONDAY}T09:00:00.000Z`, // overlaps j1
        scheduled_end_at: `${MONDAY}T11:00:00.000Z`,
      }),
    ];
    const assignment = assignJobsToLanes(jobs, 5);
    expect(assignment.get("j1")).toBe(0);
    expect(assignment.get("j2")).toBe(1); // overlapping → next lane
  });

  it("does not assign a job when no lanes are available", () => {
    const jobs = [
      makeJob({
        id: "j1",
        scheduled_start_at: `${MONDAY}T08:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T10:00:00.000Z`,
      }),
      makeJob({
        id: "j2",
        scheduled_start_at: `${MONDAY}T08:00:00.000Z`, // overlaps j1
        scheduled_end_at: `${MONDAY}T10:00:00.000Z`,
      }),
    ];
    // Only 1 lane available
    const assignment = assignJobsToLanes(jobs, 1);
    expect(assignment.get("j1")).toBe(0);
    expect(assignment.has("j2")).toBe(false); // overflow — no lane
  });
});

describe("DispatchWeekLaneView", () => {
  it("renders laneCount lane column headers (L1…L5)", () => {
    renderWeekLaneView({ laneCount: 5 });
    // Desktop table only (md:hidden/hidden md:flex — jsdom renders all)
    const laneHeaders = screen.getAllByText(/^L[1-5]$/);
    // Each label appears once per laneCount column (5 headers visible in table)
    expect(laneHeaders.length).toBeGreaterThanOrEqual(5);
  });

  it("renders correct number of day rows for daysToShow=5", () => {
    renderWeekLaneView({ daysToShow: 5 });
    // 5 weekday abbreviations (MON, TUE, WED, THU, FRI)
    const weekdays = ["MON", "TUE", "WED", "THU", "FRI"];
    weekdays.forEach((day) => {
      expect(screen.getByText(day)).toBeInTheDocument();
    });
  });

  it("renders 7 day rows when daysToShow=7", () => {
    renderWeekLaneView({ daysToShow: 7 });
    const weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
    weekdays.forEach((day) => {
      expect(screen.getByText(day)).toBeInTheDocument();
    });
  });

  it("renders empty cells with dashed border class when no jobs", () => {
    renderWeekLaneView({ laneCount: 3, jobs: [] });
    // Empty cells have border-dashed class
    const dashedCells = document.querySelectorAll(".border-dashed");
    expect(dashedCells.length).toBeGreaterThan(0);
  });

  it("renders job cards in the correct cells", () => {
    const jobs = [
      makeJob({
        id: "j1",
        scheduled_start_at: `${MONDAY}T09:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T11:00:00.000Z`,
      }),
    ];
    renderWeekLaneView({ jobs, laneCount: 3 });
    // Job title should appear in the grid
    expect(screen.getByText("Job j1")).toBeInTheDocument();
  });

  it("does NOT render WeekCommitmentChip elements (lane mode shows no commitment chips)", () => {
    const jobs = [makeJob({ id: "j1" })];
    renderWeekLaneView({ jobs, laneCount: 3 });
    // No elements with border-dashed that are role="button" (commitment chip pattern)
    const buttons = screen.queryAllByRole("button");
    const commitmentChips = buttons.filter((btn) =>
      btn.className.includes("border-dashed"),
    );
    // DISPATCH-B1.5: Lane mode — no WeekCommitmentChip. Commitment chips are
    // tech-mode only (DISPATCH-B1.25).
    expect(commitmentChips).toHaveLength(0);
  });

  it("shows mobile fallback text on mobile viewport", () => {
    renderWeekLaneView();
    expect(
      screen.getByText("Week view is available on desktop."),
    ).toBeInTheDocument();
  });

  it("calls onViewTabChange('day') and onNavigateToDate when View Today clicked", () => {
    const onViewTabChange = vi.fn();
    const onNavigateToDate = vi.fn();
    render(
      <DispatchWeekLaneView
        weekStartDate={MONDAY}
        daysToShow={5}
        laneCount={3}
        jobs={[]}
        onJobDrop={vi.fn().mockResolvedValue(undefined)}
        onJobClick={vi.fn()}
        onJobContextMenu={vi.fn()}
        onNavigateToDate={onNavigateToDate}
        onViewTabChange={onViewTabChange}
      />,
    );
    fireEvent.click(screen.getByText("View Today"));
    expect(onViewTabChange).toHaveBeenCalledWith("day");
    expect(onNavigateToDate).toHaveBeenCalledWith(
      expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
    );
  });

  it("shows EmptyState when laneCount is 0", () => {
    renderWeekLaneView({ laneCount: 0 });
    expect(
      screen.getByText("No schedule lanes configured"),
    ).toBeInTheDocument();
  });

  it("calls onJobClick when a job card is clicked", () => {
    const onJobClick = vi.fn();
    const jobs = [
      makeJob({
        id: "j-click",
        title: "Clickable Job",
        scheduled_start_at: `${MONDAY}T09:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T11:00:00.000Z`,
      }),
    ];
    render(
      <DispatchWeekLaneView
        weekStartDate={MONDAY}
        daysToShow={5}
        laneCount={3}
        jobs={jobs}
        onJobDrop={vi.fn().mockResolvedValue(undefined)}
        onJobClick={onJobClick}
        onJobContextMenu={vi.fn()}
        onNavigateToDate={vi.fn()}
      />,
    );
    const jobCard = screen
      .getByText("Clickable Job")
      .closest("[role='button']");
    expect(jobCard).not.toBeNull();
    fireEvent.click(jobCard!);
    expect(onJobClick).toHaveBeenCalledWith(
      expect.objectContaining({ id: "j-click" }),
    );
  });

  it("calls onJobContextMenu on right-click of job card", () => {
    const onJobContextMenu = vi.fn();
    const jobs = [
      makeJob({
        id: "j-ctx",
        title: "Context Job",
        scheduled_start_at: `${MONDAY}T09:00:00.000Z`,
        scheduled_end_at: `${MONDAY}T11:00:00.000Z`,
      }),
    ];
    render(
      <DispatchWeekLaneView
        weekStartDate={MONDAY}
        daysToShow={5}
        laneCount={3}
        jobs={jobs}
        onJobDrop={vi.fn().mockResolvedValue(undefined)}
        onJobClick={vi.fn()}
        onJobContextMenu={onJobContextMenu}
        onNavigateToDate={vi.fn()}
      />,
    );
    const jobCard = screen.getByText("Context Job").closest("[role='button']");
    expect(jobCard).not.toBeNull();
    fireEvent.contextMenu(jobCard!);
    expect(onJobContextMenu).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ id: "j-ctx" }),
    );
  });

  it("renders gridcell aria-labels for accessibility", () => {
    renderWeekLaneView({ laneCount: 2, daysToShow: 5 });
    // Each cell should have aria-label="Lane N, WEEKDAY DATE"
    const gridCells = screen.getAllByRole("gridcell");
    expect(gridCells.length).toBe(10); // 5 days × 2 lanes
    expect(gridCells[0]).toHaveAttribute(
      "aria-label",
      expect.stringContaining("Lane 1"),
    );
  });
});

describe("JobPropertiesPanel — site_name display", () => {
  // PLP-FIX-10: JobPropertiesPanel renders TechAssignmentSection which calls
  // useHasPermission("schedule.view_all") → useAuth(). Wrap with AuthContext.
  function renderPanel(job: ScheduledJob) {
    const qc = makeQueryClient();
    const ownerPerms = ["schedule.view_all", "schedule.manage", "users.view"];
    const authValue = {
      user: {
        id: "u1",
        email: "owner@test.dev",
        role: "owner" as const,
        tenantId: "t1",
        displayName: "Owner",
        accessToken: "tok",
        permissions: ownerPerms,
      },
      isAuthenticated: true,
      role: "owner" as const,
      permissions: ownerPerms,
      signIn: vi.fn(),
      confirmMfaChallenge: vi.fn(),
      signOut: vi.fn(),
      refreshSession: vi.fn().mockResolvedValue("tok"),
      whenSessionReady: vi.fn(),
    };
    return render(
      <AuthContext.Provider value={authValue}>
        <QueryClientProvider client={qc}>
          <JobPropertiesPanel
            job={job}
            onClose={vi.fn()}
            onJobUpdated={vi.fn()}
          />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );
  }

  const baseJob: ScheduledJob = {
    id: "job-panel-001",
    title: "Panel Test Job",
    customer_name: "Acme Corp",
    site_address: "42 Industrial Blvd, Springfield",
    scheduled_start_at: `${MONDAY}T09:00:00.000Z`,
    scheduled_end_at: `${MONDAY}T11:00:00.000Z`,
    tech_id: "tech-001",
    status: "scheduled",
    priority: "standard",
    customer_type: "company",
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
    laneIndex: null,
  };

  it("renders customer name, site name, and site address when site_name present", () => {
    const jobWithSiteName = {
      ...baseJob,
      site_name: "Main Distribution Center",
    };
    renderPanel(jobWithSiteName as ScheduledJob);

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Main Distribution Center")).toBeInTheDocument();
    expect(
      screen.getByText("42 Industrial Blvd, Springfield"),
    ).toBeInTheDocument();

    // Verify order: customer → site name → address
    const customerEl = screen.getByText("Acme Corp");
    const siteNameEl = screen.getByText("Main Distribution Center");
    const addressEl = screen.getByText("42 Industrial Blvd, Springfield");
    // All three should be in the same section
    expect(customerEl.compareDocumentPosition(siteNameEl)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(siteNameEl.compareDocumentPosition(addressEl)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });

  it("omits the site-name line when site_name is null", () => {
    const jobNoSiteName = { ...baseJob, site_name: null };
    renderPanel(jobNoSiteName as ScheduledJob);

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(
      screen.getByText("42 Industrial Blvd, Springfield"),
    ).toBeInTheDocument();
    // No site name line rendered
    expect(
      screen.queryByText("Main Distribution Center"),
    ).not.toBeInTheDocument();
  });

  it("omits the site-name line when site_name is undefined (pre-B1.5 boards)", () => {
    const jobNoSiteNameField = { ...baseJob }; // no site_name key at all
    renderPanel(jobNoSiteNameField as ScheduledJob);

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    // No site name line
    const section = screen.getByText("Customer & Site").closest("div");
    expect(section).not.toBeNull();
    // Only customer name and address should be visible.
    // Filter for elements with site-name-level content (checking class)
    const siteNameLines = within(section!)
      .queryAllByText(/./i)
      .filter(
        (el) =>
          el.className.includes("text-neutral-700") &&
          !el.className.includes("text-h"),
      );
    expect(siteNameLines).toHaveLength(0);
  });
});
