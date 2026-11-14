/**
 * DISPATCH-B2 Integration Tests — FilterBar replaces FilterSidebar
 *
 * Location: apps/web/src/__tests__/batch_dispatch_b2/dispatch_b2.integration.test.tsx
 *
 * Verifies:
 *   1. DispatchBoardPage renders FilterBar (not FilterSidebar) in the DOM
 *   2. Status pill click drives the Zustand filter state end-to-end
 *   3. RBAC: board is gated to owner/operator; tech role sees nothing
 *   4. resetStatusFilter store action works correctly
 *
 * Notes:
 *   - normalizeJob() sets status="scheduled" for all tech-assigned jobs with a start time.
 *     The integration test asserts filter state via the Zustand store (authoritative truth).
 *   - No assertion on total grid row counts — fixture counts can vary.
 *   - FilterBar uses aria-label="Dispatch board filter bar"; FilterSidebar uses "Dispatch board filters".
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
  beforeEach,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

import { DispatchBoardPage } from "../../features/dispatch-board/components/DispatchBoardPage";
import { useDispatchBoardStore } from "../../features/dispatch-board/store";

// ─── Next.js navigation mock ──────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/schedule",
  useSearchParams: () => new URLSearchParams(),
}));

// ─── MSW server ───────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);

/**
 * Two assigned jobs with known IDs.
 * normalizeJob assigns them status="scheduled" because tech_id is non-null
 * and scheduled_start_at is non-null.
 */
const BOARD_RESPONSE = {
  start_date: `${TODAY}T00:00:00Z`,
  end_date: `${TODAY}T23:59:59Z`,
  techs: [
    {
      tech_id: "tech-b2-001",
      id: "tech-b2-001",
      name: "Jake Rodriguez",
      display_color: "#3B82F6",
      avatar_url: null,
      eta_minutes_to_first_job: null,
      additional_job_commitments: [],
      jobs: [
        {
          id: "job-b2-001",
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
          version: 1,
          primary_assignment_id: "assign-b2-001",
          assignment_version: 1,
          job_number: "JOB-B2-001",
          customer_name: "Acme Corp",
          site_address: "100 Main St",
          title: null,
          assignment_role: "primary",
        },
        {
          id: "job-b2-002",
          tenant_id: "t1",
          customer_id: "c2",
          site_id: "s2",
          status_id: "st1",
          scheduled_start_at: `${TODAY}T13:00:00.000Z`,
          scheduled_end_at: `${TODAY}T15:00:00.000Z`,
          estimated_duration_minutes: 120,
          external_calendar_event_id: null,
          is_active: true,
          eta_minutes: null,
          version: 1,
          primary_assignment_id: "assign-b2-002",
          assignment_version: 1,
          job_number: "JOB-B2-002",
          customer_name: "Beta LLC",
          site_address: "200 Oak Ave",
          title: null,
          assignment_role: "primary",
        },
      ],
    },
  ],
  unassigned: [],
};

const server = setupServer(
  http.get("/api/v1/scheduling/dispatch-board", () =>
    HttpResponse.json(BOARD_RESPONSE),
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
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  // Reset store filters between tests
  useDispatchBoardStore.getState().clearAllFilters();
});
afterAll(() => server.close());

// ─── Auth context helpers ─────────────────────────────────────────────────────

function makeOwnerAuth(): AuthContextValue {
  // PLP-FIX-10: include schedule.view_all to mirror prod grants (owner has
  // * wildcard in prod; static map doesn't include schedule.view_all).
  const ownerPerms = ["schedule.view_all", "schedule.manage", "users.view"];
  return {
    user: {
      id: "user-001",
      email: "owner@example.com",
      role: "owner",
      tenantId: "tenant-001",
      displayName: "Tom Owner",
      accessToken: "tok",
      permissions: ownerPerms,
    } as AuthContextValue["user"],
    isAuthenticated: true,
    role: "owner",
    permissions: ownerPerms,
    signIn: vi.fn() as AuthContextValue["signIn"],
    confirmMfaChallenge: vi.fn() as AuthContextValue["confirmMfaChallenge"],
    signOut: vi.fn(),
    refreshSession: vi
      .fn()
      .mockResolvedValue("tok") as AuthContextValue["refreshSession"],
  };
}

function makeTechAuth(): AuthContextValue {
  return {
    ...makeOwnerAuth(),
    user: {
      ...makeOwnerAuth().user!,
      role: "technician",
    },
    role: "technician",
  };
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderPage(auth: AuthContextValue = makeOwnerAuth()) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <AuthContext.Provider value={auth}>
      <QueryClientProvider client={qc}>
        <DispatchBoardPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("DISPATCH-B2 — FilterBar integration", () => {
  beforeEach(() => {
    useDispatchBoardStore.getState().clearAllFilters();
  });

  it("1. FilterBar IS in the DOM (aria-label present)", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByLabelText("Dispatch board filter bar"),
      ).toBeInTheDocument();
    });
  });

  it("2. FilterSidebar aside is NOT in the DOM (soft-deleted from composition)", async () => {
    renderPage();
    // Wait for the page to settle
    await waitFor(() => {
      expect(
        screen.getByLabelText("Dispatch board filter bar"),
      ).toBeInTheDocument();
    });
    // The old FilterSidebar aside must not be present
    expect(
      screen.queryByLabelText("Dispatch board filters"),
    ).not.toBeInTheDocument();
  });

  it("3. Clicking 'Scheduled' status pill drives the Zustand statuses state", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByLabelText("Dispatch board filter bar"),
      ).toBeInTheDocument();
    });

    // Initially no status filters
    expect(useDispatchBoardStore.getState().filters.statuses).toHaveLength(0);

    const scheduledPill = screen.getByRole("button", { name: /^scheduled$/i });
    fireEvent.click(scheduledPill);

    // Store should now have "scheduled" in statuses
    expect(useDispatchBoardStore.getState().filters.statuses).toContain(
      "scheduled",
    );
  });

  it("4. Clicking 'All' pill after filtering clears only the status dimension", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByLabelText("Dispatch board filter bar"),
      ).toBeInTheDocument();
    });

    // Set a status filter first
    fireEvent.click(screen.getByRole("button", { name: /^scheduled$/i }));
    expect(useDispatchBoardStore.getState().filters.statuses).toContain(
      "scheduled",
    );

    // Click "All" — should reset status only
    fireEvent.click(screen.getByRole("button", { name: /^all$/i }));
    expect(useDispatchBoardStore.getState().filters.statuses).toHaveLength(0);
  });

  it("5. RBAC: owner/operator sees the board FilterBar", async () => {
    renderPage(makeOwnerAuth());
    await waitFor(() => {
      expect(
        screen.getByLabelText("Dispatch board filter bar"),
      ).toBeInTheDocument();
    });
  });

  it("6. RBAC: tech role does NOT see the dispatch board", async () => {
    renderPage(makeTechAuth());
    // The RoleGate hides the board for tech — FilterBar should not be present
    await waitFor(() => {
      expect(
        screen.queryByLabelText("Dispatch board filter bar"),
      ).not.toBeInTheDocument();
    });
  });
});

// ─── Store unit tests — resetStatusFilter ────────────────────────────────────

describe("DispatchBoardStore — resetStatusFilter (DISPATCH-B2)", () => {
  it("resetStatusFilter clears only statuses, leaves other dimensions unchanged", () => {
    // Always use useDispatchBoardStore.getState() AFTER mutations — store snapshot is immutable
    useDispatchBoardStore.getState().clearAllFilters();

    useDispatchBoardStore.getState().toggleStatusFilter("scheduled");
    useDispatchBoardStore.getState().toggleStatusFilter("confirmed");
    // DISPATCH-B3: "urgent" (was "rush")
    useDispatchBoardStore.getState().togglePriorityFilter("urgent");
    useDispatchBoardStore.getState().toggleTechFilter("tech-001");

    expect(useDispatchBoardStore.getState().filters.statuses).toHaveLength(2);
    expect(useDispatchBoardStore.getState().filters.priorities).toHaveLength(1);
    expect(useDispatchBoardStore.getState().filters.techIds).toHaveLength(1);

    // resetStatusFilter should clear ONLY statuses
    useDispatchBoardStore.getState().resetStatusFilter();

    const updated = useDispatchBoardStore.getState().filters;
    expect(updated.statuses).toHaveLength(0);
    expect(updated.priorities).toHaveLength(1); // unchanged
    expect(updated.techIds).toHaveLength(1); // unchanged

    // Cleanup
    useDispatchBoardStore.getState().clearAllFilters();
  });

  it("resetStatusFilter is a no-op when statuses is already empty", () => {
    useDispatchBoardStore.getState().clearAllFilters();
    useDispatchBoardStore.getState().resetStatusFilter();
    expect(useDispatchBoardStore.getState().filters.statuses).toHaveLength(0);
  });
});
