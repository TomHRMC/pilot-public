/**
 * MSW Handlers — Dispatch Board Lane Redesign (MKT-B11-D)
 * Updated FE-B30: Added MOCK_TECHS with name + display_color for week view tests.
 * Updated DISPATCH-B1: Added /scheduling/jobs/:id/move + /check-conflicts handlers.
 * Updated DISPATCH-B1.25: Added additional_job_commitments fixtures + commitment-only tech.
 *
 * Location: apps/web/src/mocks/handlers/dispatchBoardHandlers.ts
 *
 * Handlers added in this batch:
 *   - GET /api/v1/subscription-tiers/ — returns charter tier with schedule_lanes: 5
 *   - PATCH /api/v1/jobs/:id — job schedule/status/notes updates
 *   - POST /api/v1/scheduling/jobs/:id/check-conflicts — DISPATCH-B1
 *   - POST /api/v1/scheduling/jobs/:id/move — DISPATCH-B1
 *
 * FE-B30: Exports MOCK_TECHS + MOCK_BOARD_JOBS for use in integration tests.
 * DISPATCH-B1.25: Exports MOCK_COMMITMENT_JOB_ID + MOCK_COMMITMENT_ONLY_TECH_ID.
 *
 * Per batch-mkt-b11-dispatch-react-engr-prompt.md §Task 7
 * Updated per batch-fe-b30-react-engr-prompt.md §STEP 7
 * Updated per DISPATCH-B1 react-engr-prompt.md §MSW Handlers
 * Updated per DISPATCH-B1.25 react-engr-prompt.md §MSW Handlers
 */

import { http, HttpResponse } from "msw";
import type { components } from "@pilot/shared-types";

// ─── FE-B30: Realistic tech fixture (name + display_color required for week view) ──

/* eslint-disable pilot/no-hardcoded-design-values */
// Hex values are token-aligned: brand-500, margin-500
export const MOCK_TECHS_B30 = [
  {
    id: "tech-00000001-0000-0000-0000-000000000001",
    tech_id: "tech-00000001-0000-0000-0000-000000000001",
    name: "Jake Rodriguez",
    display_color: "#3B82F6",
    avatar_url: null,
  },
  {
    id: "tech-00000002-0000-0000-0000-000000000002",
    tech_id: "tech-00000002-0000-0000-0000-000000000002",
    name: "Maria Santos",
    display_color: "#10B981",
    avatar_url: null,
  },
];
/* eslint-enable pilot/no-hardcoded-design-values */

// ─── FE-B30: Realistic job fixture for week view tests ────────────────────────

export const TODAY = new Date().toISOString().slice(0, 10);

export const MOCK_BOARD_JOBS_B30 = [
  {
    id: "job-b30-001",
    title: "Panel upgrade — 200A service",
    customer_name: "Riverside Office Park",
    site_address: "123 Main St, Springfield",
    scheduled_start_at: `${TODAY}T09:00:00.000Z`,
    scheduled_end_at: `${TODAY}T12:00:00.000Z`,
    tech_id: "tech-00000001-0000-0000-0000-000000000001",
    status: "scheduled" as const,
    // DISPATCH-B3: real classification values
    priority: "standard" as const,
    customer_type: "company" as const,
    site_type: "commercial" as const,
    job_type_code: "panel_upgrade",
    job_type_label: "Panel Upgrade",
    updated_at: new Date().toISOString(),
    display_color: "#3B82F6", // eslint-disable-line pilot/no-hardcoded-design-values
  },
  {
    id: "job-b30-002",
    title: "Breaker replacement — emergency",
    customer_name: "Johnson Residence",
    site_address: "456 Oak Ave, Springfield",
    scheduled_start_at: `${TODAY}T13:00:00.000Z`,
    scheduled_end_at: `${TODAY}T15:00:00.000Z`,
    tech_id: "tech-00000002-0000-0000-0000-000000000002",
    status: "in_progress" as const,
    // DISPATCH-B3: urgent (was rush), person (was residential)
    priority: "urgent" as const,
    customer_type: "person" as const,
    site_type: "residential" as const,
    job_type_code: "repair",
    job_type_label: "Repair",
    updated_at: new Date().toISOString(),
    display_color: "#10B981", // eslint-disable-line pilot/no-hardcoded-design-values
  },
];

type SubscriptionTiersListResponse =
  components["schemas"]["SubscriptionTiersListResponse"];

// Fixture values from an earlier pricing draft (tests depend on them). Canonical
// pricing: Starter $59 / Teams $179 monthly ($49 / $149 billed annually),
// Charter $49, unlimited users.
const MOCK_CHARTER_TIER: components["schemas"]["SubscriptionTierResponse"] = {
  tier_id: "tier-charter-001",
  tier_name: "charter",
  display_label: "Charter",
  monthly_price_cents: 9900,
  annual_price_cents: 0,
  is_trial: false,
  trial_duration_days: null,
  schedule_lanes: 5,
  display_order: 1,
  is_active: true,
  free_period_days: 90,
  requires_payment_method: false,
  signup_cap: 12,
  price_locked: true,
};

const MOCK_TIERS_RESPONSE: SubscriptionTiersListResponse = {
  tiers: [MOCK_CHARTER_TIER],
};

/**
 * @deprecated — superseded by MOCK_DISPATCH_BOARD_RESPONSE_B1 below.
 * Kept for reference but no longer used. Remove when DispatchGrid tests migrate.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _MOCK_DISPATCH_BOARD_RESPONSE_LEGACY = () => {
  const today = new Date().toISOString().slice(0, 10);
  return {
    start_date: `${today}T00:00:00Z`,
    end_date: `${today}T23:59:59Z`,
    techs: [
      {
        tech_id: "tech-00000001-0000-0000-0000-000000000001",
        id: "tech-00000001-0000-0000-0000-000000000001",
        name: "Jake Rodriguez",
        display_color: "#3B82F6", // eslint-disable-line pilot/no-hardcoded-design-values
        avatar_url: null,
        eta_minutes_to_first_job: null,
        jobs: [
          {
            id: "job-b30-001",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000001-0000-0000-0000-000000000001",
            site_id: "site-00000001-0000-0000-0000-000000000001",
            status_id: "status-00000001-0000-0000-0000-000000000001",
            scheduled_start_at: `${today}T09:00:00.000Z`,
            scheduled_end_at: `${today}T12:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
          },
          {
            id: "job-b30-002",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000002-0000-0000-0000-000000000002",
            site_id: "site-00000002-0000-0000-0000-000000000002",
            status_id: "status-00000002-0000-0000-0000-000000000002",
            scheduled_start_at: `${today}T13:00:00.000Z`,
            scheduled_end_at: `${today}T15:00:00.000Z`,
            estimated_duration_minutes: 120,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
          },
        ],
      },
      {
        tech_id: "tech-00000002-0000-0000-0000-000000000002",
        id: "tech-00000002-0000-0000-0000-000000000002",
        name: "Maria Santos",
        display_color: "#10B981", // eslint-disable-line pilot/no-hardcoded-design-values
        avatar_url: null,
        eta_minutes_to_first_job: null,
        jobs: [
          {
            id: "job-b30-003",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000003-0000-0000-0000-000000000003",
            site_id: "site-00000003-0000-0000-0000-000000000003",
            status_id: "status-00000003-0000-0000-0000-000000000003",
            scheduled_start_at: `${today}T08:00:00.000Z`,
            scheduled_end_at: `${today}T11:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
          },
        ],
      },
    ],
    unassigned: [
      {
        id: "job-b30-004",
        tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
        customer_id: "cust-00000004-0000-0000-0000-000000000004",
        site_id: "site-00000004-0000-0000-0000-000000000004",
        status_id: "status-00000004-0000-0000-0000-000000000004",
        scheduled_start_at: null,
        scheduled_end_at: null,
        estimated_duration_minutes: null,
        external_calendar_event_id: null,
        is_active: true,
        eta_minutes: null,
      },
    ],
  };
};

// ─── DISPATCH-B1: enhanced dispatch board response (includes B1 fields) ──────
// ─── DISPATCH-B1.25: commitment fixture IDs (exported for integration tests) ──

/**
 * Job that appears as a commitment under Maria Santos (she is a helper on this job).
 * The same job also appears as a primary under Jake Rodriguez.
 */
export const MOCK_COMMITMENT_JOB_ID = "job-b30-001"; // same as Jake's primary job

/** Tech with ONLY commitment assignments (no primary jobs) — commitment-only tech. */
export const MOCK_COMMITMENT_ONLY_TECH_ID =
  "tech-00000003-0000-0000-0000-000000000003";

/** Add N days to a YYYY-MM-DD string (used only in MSW mock factory) */
function _addDaysMock(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Generates mock board data anchored to the given date (defaults to today).
 * Accepts an optional anchorDate so navigation to past/future weeks still
 * returns realistic job dates that the week grid can render.
 *
 * Jobs are spread across the week (Mon+0 through Mon+4) so the week view
 * shows populated cells on multiple days, not just the first day.
 */
const MOCK_DISPATCH_BOARD_RESPONSE_B1 = (anchorDate?: string) => {
  const mon = anchorDate ?? new Date().toISOString().slice(0, 10);
  // Spread jobs across Mon/Tue/Wed/Thu/Fri of the requested week
  const day0 = mon;
  const day1 = _addDaysMock(mon, 1);
  const day2 = _addDaysMock(mon, 2);
  const day3 = _addDaysMock(mon, 3);
  return {
    start_date: `${mon}T00:00:00Z`,
    end_date: `${_addDaysMock(mon, 6)}T23:59:59Z`,
    techs: [
      {
        tech_id: "tech-00000001-0000-0000-0000-000000000001",
        id: "tech-00000001-0000-0000-0000-000000000001",
        name: "Jake Rodriguez",
        display_color: "#3B82F6", // eslint-disable-line pilot/no-hardcoded-design-values
        avatar_url: null,
        eta_minutes_to_first_job: null,
        // DISPATCH-B1.25: Jake has no commitments (he is the primary on all his jobs)
        additional_job_commitments: [],
        jobs: [
          {
            id: "job-b30-001",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000001-0000-0000-0000-000000000001",
            site_id: "site-00000001-0000-0000-0000-000000000001",
            status_id: "status-00000001-0000-0000-0000-000000000001",
            scheduled_start_at: `${day0}T09:00:00.000Z`,
            scheduled_end_at: `${day0}T12:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
            version: 3,
            primary_assignment_id:
              "assign-00000001-0000-0000-0000-000000000001",
            assignment_version: 2,
            job_number: "JOB-001",
            customer_name: "Riverside Office Park",
            site_address: "123 Main St, Springfield",
            site_name: "Main Office",
            title: null,
            assignment_role: "primary",
            // DISPATCH-B3: real classification fields from CLASS-B1
            priority: "emergency",
            customer_type: "company",
            site_type: "commercial",
            job_type_code: "panel_upgrade",
            job_type_label: "Panel Upgrade",
          },
          {
            id: "job-b30-005",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000002-0000-0000-0000-000000000002",
            site_id: "site-00000002-0000-0000-0000-000000000002",
            status_id: "status-00000001-0000-0000-0000-000000000001",
            scheduled_start_at: `${day2}T10:00:00.000Z`,
            scheduled_end_at: `${day2}T13:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
            version: 1,
            primary_assignment_id:
              "assign-00000005-0000-0000-0000-000000000005",
            assignment_version: 1,
            job_number: "JOB-005",
            customer_name: "Metro Properties LLC",
            site_address: "789 Central Ave, Springfield",
            title: null,
            assignment_role: "primary",
            // DISPATCH-B3: standard priority, company customer
            priority: "standard",
            customer_type: "company",
            site_type: "industrial",
            job_type_code: "service_call",
            job_type_label: "Service Call",
          },
        ],
      },
      {
        tech_id: "tech-00000002-0000-0000-0000-000000000002",
        id: "tech-00000002-0000-0000-0000-000000000002",
        name: "Maria Santos",
        display_color: "#10B981", // eslint-disable-line pilot/no-hardcoded-design-values
        avatar_url: null,
        eta_minutes_to_first_job: null,
        jobs: [
          {
            id: "job-b30-003",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000003-0000-0000-0000-000000000003",
            site_id: "site-00000003-0000-0000-0000-000000000003",
            status_id: "status-00000003-0000-0000-0000-000000000003",
            scheduled_start_at: `${day1}T08:00:00.000Z`,
            scheduled_end_at: `${day1}T11:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
            version: 1,
            primary_assignment_id:
              "assign-00000003-0000-0000-0000-000000000003",
            assignment_version: 1,
            job_number: "JOB-003",
            customer_name: "Johnson Residence",
            site_address: "456 Oak Ave, Springfield",
            title: null,
            assignment_role: "primary",
            // DISPATCH-B3: urgent priority, person customer
            priority: "urgent",
            customer_type: "person",
            site_type: "residential",
            job_type_code: "panel_upgrade",
            job_type_label: "Panel Upgrade",
          },
          {
            id: "job-b30-006",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000004-0000-0000-0000-000000000004",
            site_id: "site-00000004-0000-0000-0000-000000000004",
            status_id: "status-00000003-0000-0000-0000-000000000003",
            scheduled_start_at: `${day3}T14:00:00.000Z`,
            scheduled_end_at: `${day3}T17:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
            version: 1,
            primary_assignment_id:
              "assign-00000006-0000-0000-0000-000000000006",
            assignment_version: 1,
            job_number: "JOB-006",
            customer_name: "Apex Commercial LLC",
            site_address: "321 Business Park Dr, Springfield",
            title: null,
            assignment_role: "primary",
            // DISPATCH-B3: standard priority, company customer
            priority: "standard",
            customer_type: "company",
            site_type: "commercial",
            job_type_code: "wiring",
            job_type_label: "Wiring",
          },
        ],
        // DISPATCH-B1.25: Maria is a helper on JOB-001 (Jake's primary job).
        // This appears as a commitment chip in her row.
        additional_job_commitments: [
          {
            id: "job-b30-001",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000001-0000-0000-0000-000000000001",
            site_id: "site-00000001-0000-0000-0000-000000000001",
            status_id: "status-00000001-0000-0000-0000-000000000001",
            scheduled_start_at: `${day0}T09:00:00.000Z`,
            scheduled_end_at: `${day0}T12:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
            version: 3,
            primary_assignment_id: null,
            assignment_version: null,
            job_number: "JOB-001",
            customer_name: "Riverside Office Park",
            site_address: "123 Main St, Springfield",
            title: null,
            assignment_role: "helper",
            priority: "emergency",
            customer_type: "company",
            site_type: "commercial",
            job_type_code: "panel_upgrade",
            job_type_label: "Panel Upgrade",
          },
        ],
      },
      // DISPATCH-B1.25: Commitment-only tech — has NO primary jobs, only commitment chips.
      // Verifies that a tech with only helper assignments gets a visible row.
      {
        tech_id: MOCK_COMMITMENT_ONLY_TECH_ID,
        id: MOCK_COMMITMENT_ONLY_TECH_ID,
        name: "Alex Park",
        display_color: "#6366F1", // eslint-disable-line pilot/no-hardcoded-design-values
        avatar_url: null,
        eta_minutes_to_first_job: null,
        jobs: [], // no primary jobs
        additional_job_commitments: [
          {
            id: "job-b30-005",
            tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
            customer_id: "cust-00000002-0000-0000-0000-000000000002",
            site_id: "site-00000002-0000-0000-0000-000000000002",
            status_id: "status-00000001-0000-0000-0000-000000000001",
            scheduled_start_at: `${day2}T10:00:00.000Z`,
            scheduled_end_at: `${day2}T13:00:00.000Z`,
            estimated_duration_minutes: 180,
            external_calendar_event_id: null,
            is_active: true,
            eta_minutes: null,
            version: 1,
            primary_assignment_id: null,
            assignment_version: null,
            job_number: "JOB-005",
            customer_name: "Metro Properties LLC",
            site_address: "789 Central Ave, Springfield",
            title: null,
            assignment_role: "helper",
            priority: "standard",
            customer_type: "company",
            site_type: "industrial",
            job_type_code: "service_call",
            job_type_label: "Service Call",
          },
        ],
      },
    ],
    unassigned: [
      {
        id: "job-b30-004",
        tenant_id: "tenant-00000001-0000-0000-0000-000000000001",
        customer_id: "cust-00000004-0000-0000-0000-000000000004",
        site_id: "site-00000004-0000-0000-0000-000000000004",
        status_id: "status-00000004-0000-0000-0000-000000000004",
        // Unassigned jobs have null times — they appear in the tray, not the grid
        scheduled_start_at: null,
        scheduled_end_at: null,
        estimated_duration_minutes: null,
        external_calendar_event_id: null,
        is_active: true,
        eta_minutes: null,
        version: 1,
        primary_assignment_id: null,
        assignment_version: null,
        job_number: "JOB-004",
        customer_name: "Anonymous Client",
        site_address: null,
        title: null,
        // DISPATCH-B3: unassigned job with standard priority / person customer
        priority: "standard",
        customer_type: "person",
        site_type: null,
        job_type_code: null,
        job_type_label: null,
      },
    ],
  };
};

export { MOCK_DISPATCH_BOARD_RESPONSE_B1 };

export const dispatchBoardHandlers = [
  /**
   * GET /api/v1/scheduling/dispatch-board — real endpoint used by useDispatchBoard
   * Returns the backend DispatchBoardResponse shape (techs + unassigned) with
   * jobs anchored to the requested start_date so week/month navigation shows data.
   * DISPATCH-B1: Now returns B1 fields (version, job_number, customer_name, etc.)
   *
   * Previously returned today-only dates, which meant navigating to any other week
   * produced an empty grid (jobs had today's date, cells checked for the nav'd week).
   * Fix: read start_date from query params and anchor job times to that date.
   */
  http.get("/api/v1/scheduling/dispatch-board", ({ request }) => {
    const url = new URL(request.url);
    const startDateParam = url.searchParams.get("start_date");
    // Parse the date from the ISO datetime param (e.g. "2026-07-13T00:00:00Z")
    // Fall back to today if missing or unparseable
    let anchorDate = new Date().toISOString().slice(0, 10);
    if (startDateParam) {
      const parsed = startDateParam.slice(0, 10);
      if (/^\d{4}-\d{2}-\d{2}$/.test(parsed)) {
        anchorDate = parsed;
      }
    }
    return HttpResponse.json(MOCK_DISPATCH_BOARD_RESPONSE_B1(anchorDate));
  }),

  /**
   * GET /api/v1/scheduling/board/stream — SSE endpoint for real-time updates
   * Returns a minimal event stream for integration tests.
   */
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

  /**
   * GET /api/v1/subscription-tiers/
   * Returns the active charter tier with schedule_lanes: 5.
   * Used by useScheduleLaneCount() hook.
   */
  http.get("/api/v1/subscription-tiers/", () => {
    return HttpResponse.json(MOCK_TIERS_RESPONSE);
  }),

  /**
   * GET /api/v1/subscription-tiers (without trailing slash — belt-and-suspenders)
   */
  http.get("/api/v1/subscription-tiers", () => {
    return HttpResponse.json(MOCK_TIERS_RESPONSE);
  }),

  /**
   * PATCH /api/v1/jobs/:id — job schedule/status/notes updates from JobPropertiesPanel
   */
  http.patch<{ id: string }>(
    "/api/v1/jobs/:id",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      // Echo back a minimal updated job for tests
      return HttpResponse.json({
        id: params.id,
        title: "Updated Job",
        customer_name: "Test Customer",
        site_address: "123 Main St",
        scheduled_start_at: body.scheduled_start_at ?? null,
        scheduled_end_at: body.scheduled_end_at ?? null,
        tech_id: null,
        status: (body.status as string) ?? "scheduled",
        priority: "standard",
        customer_type: "commercial",
        job_type: "install",
        updated_at: new Date().toISOString(),
      });
    },
  ),

  /**
   * POST /api/v1/scheduling/jobs/:id/check-conflicts — DISPATCH-B1
   * Returns a no-conflict response by default.
   * Override with server.use(...) in tests for conflict scenarios.
   */
  http.post<{ id: string }>(
    "/api/v1/scheduling/jobs/:id/check-conflicts",
    async () => {
      return HttpResponse.json({
        is_feasible: true,
        conflicts: [],
        drive_time_to_next_minutes: null,
        drive_time_from_prev_minutes: null,
      });
    },
  ),

  /**
   * POST /api/v1/scheduling/jobs/:id/move — DISPATCH-B1
   * Returns a successful move response with incremented job_version.
   * Override with server.use(...) in tests for 409 staleness scenarios.
   */
  http.post<{ id: string }>(
    "/api/v1/scheduling/jobs/:id/move",
    async ({ request, params }) => {
      const body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        job_id: params.id,
        job_version: ((body.expected_job_version as number) ?? 1) + 1,
        assignment_id: "assign-mock-00000001",
        assignment_version: 2,
        tech_user_id: body.tech_user_id,
        scheduled_start_at: body.scheduled_start_at,
        scheduled_end_at: body.scheduled_end_at,
        conflicts: [],
      });
    },
  ),
];

/**
 * DISPATCH-B1: Exported MSW handler factories for per-test override.
 *
 * Usage in tests:
 *   server.use(dispatchMoveHandler409("job-b30-001", 2));
 *   server.use(dispatchConflictHandler([{ conflict_type: "double_booking", ... }]));
 */

/** Override /move to return 409 with refreshed version */
export function dispatchMoveHandler409(
  jobId: string,
  currentJobVersion: number,
) {
  return http.post<{ id: string }>(
    "/api/v1/scheduling/jobs/:id/move",
    async ({ params }) => {
      if (params.id !== jobId) return; // pass through other job IDs
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/staleness",
          title: "Job was updated",
          status: 409,
          detail: "expected_job_version mismatch",
          current_job_version: currentJobVersion,
          current_state: {
            scheduled_start_at: new Date().toISOString(),
            scheduled_end_at: new Date(
              Date.now() + 2 * 3600 * 1000,
            ).toISOString(),
          },
        },
        { status: 409 },
      );
    },
  );
}

/** Override /check-conflicts to return specific conflicts */
export function dispatchConflictHandler(
  conflicts: Array<{ conflict_type: string; description?: string }>,
  isFeasible = true,
) {
  return http.post("/api/v1/scheduling/jobs/:id/check-conflicts", async () => {
    return HttpResponse.json({
      is_feasible: isFeasible,
      conflicts,
      drive_time_to_next_minutes: null,
      drive_time_from_prev_minutes: null,
    });
  });
}
