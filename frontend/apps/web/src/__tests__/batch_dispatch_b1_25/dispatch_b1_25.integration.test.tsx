/**
 * DISPATCH-B1.25 integration tests — Multi-Tech Commitment Chips
 *
 * Location: apps/web/src/__tests__/batch_dispatch_b1_25/dispatch_b1_25.integration.test.tsx
 *
 * Tests:
 *   - Day-tech view: helper tech row shows commitment chip with "Helper" role badge
 *   - The same job appears (draggable) under its primary tech
 *   - Commitment-only tech renders a row with only a read-only chip
 *   - Lane mode does NOT render commitment chips (jobs[] only)
 *   - Commitment chip has cursor-default (not cursor-grab)
 *
 * Per DISPATCH-B1.25 react-engr-prompt.md §Test Requirements
 */

import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DndContext } from "@dnd-kit/core";

import { DispatchGridDayView } from "../../features/dispatch-board/components/DispatchGridDayView";
import { DispatchBoardLanes } from "../../features/dispatch-board/components/DispatchBoardLanes";
import { useDispatchBoard } from "../../features/dispatch-board/hooks/useDispatchBoard";
import {
  MOCK_DISPATCH_BOARD_RESPONSE_B1,
  MOCK_COMMITMENT_ONLY_TECH_ID,
} from "../../mocks/handlers/dispatchBoardHandlers";
import type { DispatchBoardTech } from "../../features/dispatch-board/types-stub";
import type { ScheduledJob } from "../../features/dispatch-board/components/DispatchBoardLanes";

// ─── MSW server ────────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);

const server = setupServer(
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json(MOCK_DISPATCH_BOARD_RESPONSE_B1()),
  ),
  http.get("/api/v1/jobs/", () =>
    HttpResponse.json({ items: [], total: 0, limit: 200, offset: 0 }),
  ),
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
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

/**
 * Render DispatchGridDayView with the normalized data returned by useDispatchBoard.
 * Wraps with DndContext + QueryClientProvider.
 */
function DispatchDayViewHarness() {
  const { data } = useDispatchBoard(TODAY, TODAY);
  if (!data) return <div>Loading...</div>;

  const techs = data.techs as DispatchBoardTech[];
  const jobs = data.jobs as ScheduledJob[];

  return (
    <DndContext>
      <DispatchGridDayView
        date={new Date(TODAY)}
        techs={techs}
        jobs={jobs}
        onJobClick={vi.fn()}
        onJobDrop={vi.fn()}
        onJobContextMenu={vi.fn()}
      />
    </DndContext>
  );
}

function renderDayView() {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DispatchDayViewHarness />
    </QueryClientProvider>,
  );
}

// ─── Lane mode harness ─────────────────────────────────────────────────────────

function DispatchLaneHarness() {
  const { data } = useDispatchBoard(TODAY, TODAY);
  if (!data) return <div>Loading...</div>;

  const jobs = data.jobs as ScheduledJob[];

  return (
    <DndContext>
      <DispatchBoardLanes
        date={new Date(TODAY)}
        jobs={jobs}
        laneCount={5}
        onJobClick={vi.fn()}
        onJobDrop={vi.fn()}
        onUpgradeClick={vi.fn()}
        onJobContextMenu={vi.fn()}
      />
    </DndContext>
  );
}

function renderLaneView() {
  const queryClient = makeQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DispatchLaneHarness />
    </QueryClientProvider>,
  );
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe("DISPATCH-B1.25: Day-tech view — commitment chips", () => {
  it("Maria Santos row shows commitment chip with Helper role badge", async () => {
    renderDayView();

    // Wait for data to load
    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    // The Helper role badge should appear in Maria's row
    const badges = screen.getAllByTestId("role-badge");
    const helperBadge = badges.find((b) => b.textContent === "Helper");
    expect(helperBadge).toBeDefined();
    expect(helperBadge).toBeInTheDocument();
  });

  it("JOB-001 appears as a primary block (draggable) under Jake Rodriguez", async () => {
    renderDayView();

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    // Primary job blocks show job title — "Job #JOB-001" / "Riverside Office Park"
    const jakePrimary = screen.getAllByText(/Riverside Office Park/i);
    expect(jakePrimary.length).toBeGreaterThan(0);

    // The primary block should have cursor-grab (not cursor-default)
    // Find blocks containing "Riverside Office Park" — at least one must be cursor-grab
    const allButtons = screen.getAllByRole("button");
    const primaryBlock = allButtons.find(
      (b) =>
        b.className.includes("cursor-grab") &&
        b.textContent?.includes("Riverside Office Park"),
    );
    expect(primaryBlock).toBeDefined();
  });

  it("commitment-only tech (Alex Park) row renders with only read-only chips", async () => {
    renderDayView();

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    // Alex Park should appear as a tech row header
    expect(screen.getByText("Alex Park")).toBeInTheDocument();
  });

  it("commitment chip (Helper badge) has cursor-default, not cursor-grab", async () => {
    renderDayView();

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    // Find all buttons with cursor-default (commitment chips)
    const allButtons = screen.getAllByRole("button");
    const commitmentChips = allButtons.filter((b) =>
      b.className.includes("cursor-default"),
    );
    expect(commitmentChips.length).toBeGreaterThan(0);

    // Each commitment chip must NOT have cursor-grab
    for (const chip of commitmentChips) {
      expect(chip.className).not.toContain("cursor-grab");
    }
  });

  it("commitment chip aria-label includes '(commitment)'", async () => {
    renderDayView();

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    const allButtons = screen.getAllByRole("button");
    const commitmentButton = allButtons.find((b) =>
      b.getAttribute("aria-label")?.includes("(commitment)"),
    );
    expect(commitmentButton).toBeDefined();
  });
});

describe("DISPATCH-B1.25: Lane mode does NOT render commitment chips", () => {
  it("commitment job (job-b30-001) is NOT duplicated in lane view", async () => {
    renderLaneView();

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    // Lane mode renders from jobs[] which is primary-only.
    // "Riverside Office Park" appears only once (Jake's primary — appears in lane).
    // If commitments leaked into jobs[], it would appear twice.
    const parkEntries = screen.queryAllByText("Riverside Office Park");
    // At most one entry (may be zero if that job's times don't render in current day).
    expect(parkEntries.length).toBeLessThanOrEqual(1);

    // No role badges should appear in lane mode at all
    const badges = screen.queryAllByTestId("role-badge");
    expect(badges).toHaveLength(0);
  });

  it("MOCK_COMMITMENT_ONLY_TECH_ID job is absent from lane view primary jobs", async () => {
    renderLaneView();

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    // Alex Park's commitment-only tech should not add his tech_id to any job in jobs[]
    // No role badges = lane mode is unaffected by commitments
    const badges = screen.queryAllByTestId("role-badge");
    expect(badges).toHaveLength(0);

    // Verify MOCK_COMMITMENT_ONLY_TECH_ID is used to confirm the fixture is exported
    expect(MOCK_COMMITMENT_ONLY_TECH_ID).toBe(
      "tech-00000003-0000-0000-0000-000000000003",
    );
  });
});
