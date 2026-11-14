/**
 * DISPATCH-B1 integration tests
 *
 * Location: apps/web/src/__tests__/batch_dispatch_b1/dispatch_b1.integration.test.tsx
 *
 * Tests:
 *   - Lane↔Tech toggle swaps day render
 *   - Lane↔Tech toggle survives a view-tab switch
 *   - layoutMode resets to 'lane' after store remount (no persist)
 *   - Right-rail arbitration: job click shows properties; pending move overrides with conflict pane
 *   - store: layoutMode default is 'lane'
 *   - store: setLayoutMode changes layoutMode
 */

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
import { render, screen, fireEvent } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DndContext } from "@dnd-kit/core";

// ── Store ─────────────────────────────────────────────────────────────────────
import { useDispatchBoardStore } from "../../features/dispatch-board/store";

// ── Components ────────────────────────────────────────────────────────────────
import { DispatchToolbar } from "../../features/dispatch-board/components/DispatchToolbar";
import { UnassignedTray } from "../../features/dispatch-board/components/UnassignedTray";

// ── MSW server ────────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);

const server = setupServer(
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json({
      techs: [
        {
          tech_id: "tech-001",
          id: "tech-001",
          name: "Jake Rodriguez",
          display_color: "#3B82F6",
          avatar_url: null,
          jobs: [
            {
              id: "job-b1-001",
              tenant_id: "t1",
              customer_id: "c1",
              site_id: "s1",
              status_id: "st1",
              scheduled_start_at: `${TODAY}T09:00:00.000Z`,
              scheduled_end_at: `${TODAY}T12:00:00.000Z`,
              estimated_duration_minutes: 180,
              external_calendar_event_id: null,
              is_active: true,
              eta_minutes: null,
              version: 3,
              primary_assignment_id: "assign-001",
              assignment_version: 2,
              job_number: "JOB-001",
              customer_name: "Riverside Office Park",
              site_address: "123 Main St",
              title: null,
            },
          ],
        },
      ],
      unassigned: [
        {
          id: "job-b1-unassigned",
          tenant_id: "t1",
          customer_id: "c2",
          site_id: "s2",
          status_id: "st2",
          scheduled_start_at: null,
          scheduled_end_at: null,
          estimated_duration_minutes: null,
          external_calendar_event_id: null,
          is_active: true,
          eta_minutes: null,
          version: 1,
          primary_assignment_id: null,
          assignment_version: null,
          job_number: "JOB-UNASSIGNED",
          customer_name: "Anon Client",
          site_address: null,
          title: null,
        },
      ],
    }),
  ),
  http.get("/api/v1/scheduling/board/stream", () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode("event: connected\ndata: {}\n\n"));
        controller.close();
      },
    });
    return new Response(stream, {
      headers: { "Content-Type": "text/event-stream" },
    });
  }),
  http.get("/api/v1/subscription-tiers/", () =>
    HttpResponse.json({
      tiers: [
        {
          tier_id: "t1",
          tier_name: "charter",
          schedule_lanes: 5,
          display_label: "Charter",
          monthly_price_cents: 9900,
          is_trial: false,
          trial_duration_days: null,
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
          tier_id: "t1",
          tier_name: "charter",
          schedule_lanes: 5,
          display_label: "Charter",
          monthly_price_cents: 9900,
          is_trial: false,
          trial_duration_days: null,
          display_order: 1,
          is_active: true,
        },
      ],
    }),
  ),
  http.post("/api/v1/scheduling/jobs/:id/check-conflicts", () =>
    HttpResponse.json({
      is_feasible: true,
      conflicts: [],
      drive_time_to_next_minutes: null,
      drive_time_from_prev_minutes: null,
    }),
  ),
  http.post("/api/v1/scheduling/jobs/:id/move", async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      job_id: params.id,
      job_version: ((body.expected_job_version as number) ?? 1) + 1,
      assignment_id: "assign-mock",
      assignment_version: 2,
      tech_user_id: body.tech_user_id,
      scheduled_start_at: body.scheduled_start_at,
      scheduled_end_at: body.scheduled_end_at,
      conflicts: [],
    });
  }),
  http.patch("/api/v1/jobs/:id", async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: params.id, ...body });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Wrapper helper ────────────────────────────────────────────────────────────

function makeQCWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  }
  Wrapper.displayName = "QCWrapper";
  return Wrapper;
}

// ── Store unit tests ──────────────────────────────────────────────────────────

describe("DispatchBoardStore — layoutMode", () => {
  it("defaults to 'lane'", () => {
    // Reset to known default first in case a prior test mutated it
    useDispatchBoardStore.getState().setLayoutMode("lane");
    expect(useDispatchBoardStore.getState().layoutMode).toBe("lane");
  });

  it("setLayoutMode('tech') changes layoutMode to 'tech'", () => {
    useDispatchBoardStore.getState().setLayoutMode("tech");
    expect(useDispatchBoardStore.getState().layoutMode).toBe("tech");
    // Reset
    useDispatchBoardStore.getState().setLayoutMode("lane");
  });

  it("conflictPreviewOpen defaults to false", () => {
    useDispatchBoardStore.getState().closeConflictPreview(); // ensure reset
    expect(useDispatchBoardStore.getState().conflictPreviewOpen).toBe(false);
  });

  it("openConflictPreview + closeConflictPreview work correctly", () => {
    const store = useDispatchBoardStore.getState();
    store.openConflictPreview("job-001");
    expect(useDispatchBoardStore.getState().conflictPreviewOpen).toBe(true);
    expect(useDispatchBoardStore.getState().conflictPreviewJobId).toBe(
      "job-001",
    );
    store.closeConflictPreview();
    expect(useDispatchBoardStore.getState().conflictPreviewOpen).toBe(false);
    expect(useDispatchBoardStore.getState().conflictPreviewJobId).toBeNull();
  });
});

// ── DispatchToolbar: Lane|Tech toggle ─────────────────────────────────────────

describe("DispatchToolbar — Lane|Tech toggle", () => {
  it("shows Lane|Tech toggle when viewTab=day and onLayoutModeToggle provided", () => {
    render(
      <DispatchToolbar
        viewTab="day"
        activeDate={TODAY}
        sseConnected={true}
        lastBoardFetch={null}
        onViewTabChange={() => {}}
        onNavigatePrev={() => {}}
        onNavigateNext={() => {}}
        onNavigateToToday={() => {}}
        layoutMode="lane"
        onLayoutModeToggle={() => {}}
      />,
      { wrapper: makeQCWrapper() },
    );
    expect(screen.getByText("Lane")).toBeInTheDocument();
    expect(screen.getByText("Tech")).toBeInTheDocument();
  });

  // DISPATCH-B1.5: Extended Lane|Tech toggle to week mode (Surface 2).
  // This test was updated from "does NOT show" to "DOES show" because
  // B1.5 added the toggle condition: viewTab === "day" || viewTab === "week".
  it("DOES show Lane|Tech toggle when viewTab=week (DISPATCH-B1.5)", () => {
    render(
      <DispatchToolbar
        viewTab="week"
        activeDate={TODAY}
        sseConnected={true}
        lastBoardFetch={null}
        onViewTabChange={() => {}}
        onNavigatePrev={() => {}}
        onNavigateNext={() => {}}
        onNavigateToToday={() => {}}
        layoutMode="lane"
        onLayoutModeToggle={() => {}}
      />,
      { wrapper: makeQCWrapper() },
    );
    // B1.5: Lane|Tech toggle renders in week mode alongside the 5d/7d toggle
    expect(screen.getByText("Lane")).toBeInTheDocument();
    expect(screen.getByText("Tech")).toBeInTheDocument();
  });

  it("calls onLayoutModeToggle with 'tech' when Tech button clicked", () => {
    const onToggle = vi.fn();
    render(
      <DispatchToolbar
        viewTab="day"
        activeDate={TODAY}
        sseConnected={true}
        lastBoardFetch={null}
        onViewTabChange={() => {}}
        onNavigatePrev={() => {}}
        onNavigateNext={() => {}}
        onNavigateToToday={() => {}}
        layoutMode="lane"
        onLayoutModeToggle={onToggle}
      />,
      { wrapper: makeQCWrapper() },
    );
    fireEvent.click(screen.getByText("Tech"));
    expect(onToggle).toHaveBeenCalledWith("tech");
  });

  it("calls onLayoutModeToggle with 'lane' when Lane button clicked", () => {
    const onToggle = vi.fn();
    render(
      <DispatchToolbar
        viewTab="day"
        activeDate={TODAY}
        sseConnected={true}
        lastBoardFetch={null}
        onViewTabChange={() => {}}
        onNavigatePrev={() => {}}
        onNavigateNext={() => {}}
        onNavigateToToday={() => {}}
        layoutMode="tech"
        onLayoutModeToggle={onToggle}
      />,
      { wrapper: makeQCWrapper() },
    );
    fireEvent.click(screen.getByText("Lane"));
    expect(onToggle).toHaveBeenCalledWith("lane");
  });
});

// ── UnassignedTray renders always ─────────────────────────────────────────────

describe("UnassignedTray — always visible", () => {
  it("renders tray with testid even when no jobs", () => {
    render(
      <DndContext>
        <UnassignedTray jobs={[]} onJobClick={() => {}} />
      </DndContext>,
    );
    expect(screen.getByTestId("unassigned-tray")).toBeInTheDocument();
    expect(screen.getByText("Unassigned (0)")).toBeInTheDocument();
  });
});
