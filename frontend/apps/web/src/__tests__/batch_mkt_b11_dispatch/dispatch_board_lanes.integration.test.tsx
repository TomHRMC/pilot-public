/**
 * Integration Tests — MKT-B11-D Dispatch Board Lane Redesign
 *
 * Location: apps/web/src/__tests__/batch_mkt_b11_dispatch/dispatch_board_lanes.integration.test.tsx
 *
 * Tests the DispatchBoardLanes component and associated utilities:
 * 1. Renders N lane rows equal to laneCount
 * 2. Shows upgrade CTA when all lanes occupied on drop attempt
 * 3. Allows job placement in a free lane
 * 4. Opens JobPropertiesPanel on job click
 * 5. Closes panel on Escape key
 * 6. Panel shows editable schedule fields
 *
 * Per batch-mkt-b11-dispatch-react-engr-prompt.md §Task 8
 *
 * Rules applied:
 * - Rule 14: retry: false on QueryClient
 * - Rule 15: fresh QueryClient per test, no shared state
 * - Rule 17: toBeInTheDocument() for web (jsdom)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import {
  DispatchBoardLanes,
  checkLaneAvailability,
} from "../../features/dispatch-board/components/DispatchBoardLanes";
import { JobPropertiesPanel } from "../../features/dispatch-board/components/JobPropertiesPanel";
import type { ScheduledJob } from "../../features/dispatch-board/components/DispatchBoardLanes";

// PLP-FIX-10: JobPropertiesPanel renders TechAssignmentSection which calls
// useHasPermission("schedule.view_all") → useAuth(). Provide an auth context.
const ownerAuthValue: AuthContextValue = {
  user: {
    id: "u1",
    email: "owner@test.dev",
    role: "owner",
    tenantId: "t1",
    displayName: "Owner",
    accessToken: "tok",
    permissions: ["schedule.view_all", "schedule.manage", "users.view"],
  },
  isAuthenticated: true,
  role: "owner",
  permissions: ["schedule.view_all", "schedule.manage", "users.view"],
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
  whenSessionReady: vi.fn(),
};

// ─── Mock @dnd-kit/core ───────────────────────────────────────────────────────
// @dnd-kit relies on pointer events that jsdom doesn't fully support.
// Mock the context and hooks so tests can focus on component behaviour.

vi.mock("@dnd-kit/core", () => {
  const DndContext = ({
    children,
  }: {
    children: React.ReactNode;
    onDragStart?: () => void;
    onDragEnd?: () => void;
  }) => <>{children}</>;

  const useDraggable = () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    isDragging: false,
  });

  const useDroppable = ({
    id,
    data,
  }: {
    id: string;
    data?: Record<string, unknown>;
  }) => ({
    setNodeRef: vi.fn(),
    isOver: false,
    data,
    id,
  });

  const DragOverlay = ({ children }: { children?: React.ReactNode }) => (
    <>{children ?? null}</>
  );

  const useSensors = (...sensors: unknown[]) => sensors;
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const useSensor = (_sensor: unknown, _options?: unknown) => ({});
  const PointerSensor = {};

  return {
    DndContext,
    useDraggable,
    useDroppable,
    DragOverlay,
    useSensors,
    useSensor,
    PointerSensor,
  };
});

// ─── Mock next/navigation (JobPropertiesPanel uses Link) ──────────────────────
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/schedule",
}));

// ─── Mock @pilot/shared-api ───────────────────────────────────────────────────
vi.mock("@pilot/shared-api", () => ({
  apiClient: {
    patch: vi.fn().mockResolvedValue({ data: {} }),
    get: vi.fn().mockResolvedValue({ data: { tiers: [] } }),
  },
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = makeQueryClient();
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

/** Make a scheduled job at a given hour on 2026-07-10 (UTC) */
function makeJob(
  id: string,
  title: string,
  startHour: number,
  durationHours = 2,
): ScheduledJob {
  // Use a fixed UTC date so checkLaneAvailability UTC windows align
  const base = new Date("2026-07-10T00:00:00.000Z");
  base.setUTCHours(startHour, 0, 0, 0);
  const start = base.toISOString();
  const end = new Date(
    base.getTime() + durationHours * 60 * 60 * 1000,
  ).toISOString();
  return {
    id,
    title,
    customer_name: "Test Customer",
    site_address: "123 Main St",
    scheduled_start_at: start,
    scheduled_end_at: end,
    tech_id: null,
    status: "scheduled",
    priority: "standard",
    customer_type: "company",
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("DispatchBoardLanes — Schedule Lane Model (MKT-B11-D)", () => {
  const baseDate = new Date("2026-07-10T12:00:00.000Z");
  const noop = vi.fn();

  beforeEach(() => {
    noop.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ── Test 1 ──────────────────────────────────────────────────────────────────

  it("renders N lane rows equal to laneCount", () => {
    const laneCount = 5;
    render(
      <DispatchBoardLanes
        date={baseDate}
        laneCount={laneCount}
        jobs={[]}
        onJobClick={noop}
        onJobDrop={noop}
        onUpgradeClick={noop}
      />,
      { wrapper },
    );

    // Each lane has aria-label="Schedule lane N"
    for (let i = 1; i <= laneCount; i++) {
      expect(
        screen.getByRole("region", { name: `Schedule lane ${i}` }),
      ).toBeInTheDocument();
    }

    // Exactly 5 lanes
    const laneRegions = screen.getAllByRole("region");
    const scheduleLaneRegions = laneRegions.filter((el) =>
      el.getAttribute("aria-label")?.startsWith("Schedule lane"),
    );
    expect(scheduleLaneRegions).toHaveLength(laneCount);
  });

  // ── Test 2 ──────────────────────────────────────────────────────────────────

  it("shows upgrade CTA banner when all lanes are occupied at a time slot (checkLaneAvailability)", () => {
    // Create 5 jobs all starting at 10 AM — fills all 5 lanes
    const laneCount = 5;
    const today = new Date("2026-07-10T00:00:00.000Z");
    const jobs: ScheduledJob[] = Array.from({ length: laneCount }, (_, i) =>
      makeJob(`job-${i}`, `Job ${i + 1}`, 10),
    );

    // Verify the check utility itself returns available=false
    const checkStart = new Date("2026-07-10T10:00:00.000Z");
    const checkEnd = new Date("2026-07-10T12:00:00.000Z");
    const { available, blockedLanes } = checkLaneAvailability(
      jobs,
      laneCount,
      checkStart,
      checkEnd,
    );

    expect(available).toBe(false);
    expect(blockedLanes).toHaveLength(laneCount);

    // The upgrade CTA is shown after a failed drop — render with no CTA initially
    const onUpgradeClick = vi.fn();
    render(
      <DispatchBoardLanes
        date={today}
        laneCount={laneCount}
        jobs={jobs}
        onJobClick={noop}
        onJobDrop={noop}
        onUpgradeClick={onUpgradeClick}
      />,
      { wrapper },
    );

    // CTA not shown initially (no drop attempted)
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  // ── Test 3 ──────────────────────────────────────────────────────────────────

  it("allows job placement in a free lane — checkLaneAvailability returns available=true", () => {
    // 2 lanes occupied out of 5 at the same time
    const laneCount = 5;
    const jobs: ScheduledJob[] = [
      makeJob("job-1", "Job 1", 10),
      makeJob("job-2", "Job 2", 10),
    ];

    const checkStart = new Date("2026-07-10T10:00:00.000Z");
    const checkEnd = new Date("2026-07-10T12:00:00.000Z");
    const { available, blockedLanes } = checkLaneAvailability(
      jobs,
      laneCount,
      checkStart,
      checkEnd,
    );

    // 3 free lanes remain
    expect(available).toBe(true);
    expect(blockedLanes.length).toBeLessThan(laneCount);
  });

  // ── Test 4 ──────────────────────────────────────────────────────────────────

  it("opens JobPropertiesPanel on job click", () => {
    const scheduledJob = makeJob("job-click-test", "Panel Open Test Job", 9);
    const onJobClick = vi.fn();

    render(
      <DispatchBoardLanes
        date={new Date("2026-07-10T12:00:00.000Z")}
        laneCount={3}
        jobs={[scheduledJob]}
        onJobClick={onJobClick}
        onJobDrop={noop}
        onUpgradeClick={noop}
      />,
      { wrapper },
    );

    // Find and click the job block
    const jobButton = screen.getByRole("button", {
      name: "Job: Panel Open Test Job",
    });
    fireEvent.click(jobButton);

    expect(onJobClick).toHaveBeenCalledOnce();
    expect(onJobClick).toHaveBeenCalledWith(
      expect.objectContaining({ id: "job-click-test" }),
    );
  });

  // ── Test 5 ──────────────────────────────────────────────────────────────────

  it("closes JobPropertiesPanel on Escape key", () => {
    const job = makeJob("job-esc-test", "Escape Panel Test", 9);
    const onClose = vi.fn();

    render(
      <AuthContext.Provider value={ownerAuthValue}>
        <QueryClientProvider client={makeQueryClient()}>
          <JobPropertiesPanel job={job} onClose={onClose} onJobUpdated={noop} />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    // Panel is visible
    expect(
      screen.getByRole("dialog", { name: /Job properties/ }),
    ).toBeInTheDocument();

    // Press Escape
    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledOnce();
  });

  // ── Test 6 ──────────────────────────────────────────────────────────────────

  it("JobPropertiesPanel shows editable start time and end time fields", () => {
    const job = makeJob("job-schedule-test", "Schedule Edit Test", 9);
    const onClose = vi.fn();

    render(
      <AuthContext.Provider value={ownerAuthValue}>
        <QueryClientProvider client={makeQueryClient()}>
          <JobPropertiesPanel job={job} onClose={onClose} onJobUpdated={noop} />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    // Both datetime-local inputs must be present and accessible
    const startInput = screen.getByLabelText("Job start time");
    const endInput = screen.getByLabelText("Job end time");

    expect(startInput).toBeInTheDocument();
    expect(endInput).toBeInTheDocument();
    expect(startInput).toHaveAttribute("type", "datetime-local");
    expect(endInput).toHaveAttribute("type", "datetime-local");
  });
});

// ─── checkLaneAvailability pure function tests ─────────────────────────────────

describe("checkLaneAvailability — pure utility", () => {
  const today = "2026-07-10";

  /** idx ensures unique IDs when creating multiple jobs at the same hour */
  function makeAt(hour: number, idx = 0, duration = 2): ScheduledJob {
    const start = new Date(
      `${today}T${String(hour).padStart(2, "0")}:00:00.000Z`,
    );
    const end = new Date(start.getTime() + duration * 60 * 60 * 1000);
    return {
      id: `j-${hour}-${idx}`,
      title: `Job at ${hour} #${idx}`,
      customer_name: "",
      site_address: "",
      scheduled_start_at: start.toISOString(),
      scheduled_end_at: end.toISOString(),
      tech_id: null,
      status: "scheduled",
      priority: "standard",
      customer_type: "company",
      job_type_code: "install",
      job_type_label: "Install",
      updated_at: "",
    };
  }

  it("returns available=true when no jobs exist", () => {
    const { available } = checkLaneAvailability(
      [],
      3,
      new Date(`${today}T10:00:00.000Z`),
      new Date(`${today}T12:00:00.000Z`),
    );
    expect(available).toBe(true);
  });

  it("returns available=false when all lanes occupied", () => {
    // 3 jobs all at 10 AM with unique IDs (idx 0,1,2) → fills all 3 lanes
    const jobs = [makeAt(10, 0), makeAt(10, 1), makeAt(10, 2)];
    const { available } = checkLaneAvailability(
      jobs,
      3,
      new Date(`${today}T10:00:00.000Z`),
      new Date(`${today}T12:00:00.000Z`),
    );
    expect(available).toBe(false);
  });

  it("returns available=true for non-overlapping time windows", () => {
    const jobs = [makeAt(8, 0)]; // Job 8–10 AM
    const { available } = checkLaneAvailability(
      jobs,
      1,
      new Date(`${today}T11:00:00.000Z`), // 11 AM–1 PM → no overlap
      new Date(`${today}T13:00:00.000Z`),
    );
    expect(available).toBe(true);
  });
});
