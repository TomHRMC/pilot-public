/**
 * MSW Handlers — /api/v1/schedule/* stubs
 *
 * Location: apps/web/src/mocks/handlers/schedule.ts
 *
 * All BE-B3 endpoints are stubbed here for:
 * - Development (dev server mock mode)
 * - Unit and integration tests (vitest + jsdom)
 *
 * SSE mock strategy: The SSE endpoint uses a ReadableStream mock that
 * emits a sequence of events then stays open. For unit tests that exercise
 * SSE event handling, use the eventSourceFactory injection on useSseChannel.
 *
 * Per batch-fe-b4-design.md §D.3
 */

import { http, HttpResponse } from "msw";
import type {
  DispatchBoardResponse,
  MoveJobResponse,
  CheckConflictsResponse,
  DriveTimeResponse,
  TechAvailability,
} from "../../features/dispatch-board/types-stub";

/* eslint-disable pilot/no-hardcoded-design-values */
// MSW fixture data: hex values are Pass 1 token values (API-driven — not arbitrary design)
const MOCK_TECHS = [
  {
    id: "tech-1",
    tech_id: "tech-1",
    name: "Mike Chen",
    display_color: "#3B43D6", // brand-600
    avatar_url: null,
  },
  {
    id: "tech-2",
    tech_id: "tech-2",
    name: "Sarah Kim",
    display_color: "#059669", // margin-600
    avatar_url: null,
  },
  {
    id: "tech-3",
    tech_id: "tech-3",
    name: "James Rivera",
    display_color: "#B45309", // alert-600
    avatar_url: null,
  },
];
/* eslint-enable pilot/no-hardcoded-design-values */

const MOCK_JOBS = [
  {
    id: "job-1",
    title: "Panel upgrade — 200A service",
    customer_name: "Riverside Office Park",
    site_address: "123 Main St, Springfield",
    scheduled_start_at: new Date()
      .toISOString()
      .replace(/T.*/, "T09:00:00.000Z"),
    scheduled_end_at: new Date().toISOString().replace(/T.*/, "T12:00:00.000Z"),
    tech_id: "tech-1",
    status: "scheduled" as const,
    priority: "standard" as const,
    customer_type: "company" as const,
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
    display_color: "#3B43D6", // eslint-disable-line pilot/no-hardcoded-design-values,
  },
  {
    id: "job-2",
    title: "Breaker replacement — emergency",
    customer_name: "Johnson Residence",
    site_address: "456 Oak Ave, Springfield",
    scheduled_start_at: new Date()
      .toISOString()
      .replace(/T.*/, "T13:00:00.000Z"),
    scheduled_end_at: new Date().toISOString().replace(/T.*/, "T15:00:00.000Z"),
    tech_id: "tech-1",
    status: "confirmed" as const,
    priority: "urgent" as const,
    customer_type: "person" as const,
    job_type_code: "service",
    job_type_label: "Service",
    updated_at: new Date().toISOString(),
    display_color: "#3B43D6", // eslint-disable-line pilot/no-hardcoded-design-values,
  },
  {
    id: "job-3",
    title: "EV charger install",
    customer_name: "Green Auto Group",
    site_address: "789 Industrial Blvd",
    scheduled_start_at: new Date()
      .toISOString()
      .replace(/T.*/, "T08:00:00.000Z"),
    scheduled_end_at: new Date().toISOString().replace(/T.*/, "T11:00:00.000Z"),
    tech_id: "tech-2",
    status: "in_progress" as const,
    priority: "standard" as const,
    customer_type: "company" as const,
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
    display_color: "#059669", // eslint-disable-line pilot/no-hardcoded-design-values,
  },
  {
    id: "job-4",
    title: "GFCI outlets — kitchen remodel",
    customer_name: "Martinez Family",
    site_address: "321 Elm St",
    scheduled_start_at: null as unknown as string,
    scheduled_end_at: null as unknown as string,
    tech_id: null,
    status: "unassigned" as const,
    priority: "standard" as const,
    customer_type: "person" as const,
    job_type_code: "service",
    job_type_label: "Service",
    updated_at: new Date().toISOString(),
    display_color: null as unknown as string,
  },
];

export const scheduleHandlers = [
  // GET /api/v1/schedule/board
  http.get("/api/v1/schedule/board", ({ request }) => {
    const url = new URL(request.url);
    const date =
      url.searchParams.get("date") ?? new Date().toISOString().split("T")[0];

    const response: DispatchBoardResponse = {
      date: date ?? "",
      techs: MOCK_TECHS,
      jobs: MOCK_JOBS,
    };

    return HttpResponse.json(response);
  }),

  // POST /api/v1/schedule/jobs/:id/reschedule
  http.post<{ id: string }>(
    "/api/v1/schedule/jobs/:id/reschedule",
    async ({ request, params }) => {
      const body = (await request.json()) as {
        expected_updated_at: string;
        scheduled_start_at: string;
        scheduled_end_at: string;
        tech_id: string | null;
      };

      // Simulate 409 staleness conflict when expected_updated_at is 'stale-version'
      if (body.expected_updated_at === "stale-version") {
        return HttpResponse.json(
          {
            status: 409,
            title: "Record updated since last view",
            detail: "The job was moved since you loaded the board.",
            refreshed_state: {
              id: params.id,
              tech_id: "tech-2",
              scheduled_start_at: new Date()
                .toISOString()
                .replace(/T.*/, "T10:00:00.000Z"),
              scheduled_end_at: new Date()
                .toISOString()
                .replace(/T.*/, "T12:00:00.000Z"),
              updated_at: new Date().toISOString(),
              tech_name: "Sarah Kim",
            },
          },
          { status: 409 },
        );
      }

      const response: MoveJobResponse = {
        id: params.id,
        tech_id: body.tech_id,
        scheduled_start_at: body.scheduled_start_at,
        scheduled_end_at: body.scheduled_end_at,
        updated_at: new Date().toISOString(),
      };

      return HttpResponse.json(response);
    },
  ),

  // POST /api/v1/schedule/jobs/:id/assign
  http.post<{ id: string }>(
    "/api/v1/schedule/jobs/:id/assign",
    async ({ request, params }) => {
      const body = (await request.json()) as {
        expected_updated_at: string;
        tech_id: string | null;
        scheduled_start_at: string;
        scheduled_end_at: string;
      };

      if (body.expected_updated_at === "stale-version") {
        return HttpResponse.json(
          {
            status: 409,
            title: "Record updated since last view",
            detail: "The job was reassigned since you loaded the board.",
            refreshed_state: {
              id: params.id,
              tech_id: "tech-3",
              updated_at: new Date().toISOString(),
              tech_name: "James Rivera",
            },
          },
          { status: 409 },
        );
      }

      const response: MoveJobResponse = {
        id: params.id,
        tech_id: body.tech_id,
        scheduled_start_at: body.scheduled_start_at,
        scheduled_end_at: body.scheduled_end_at,
        updated_at: new Date().toISOString(),
      };

      return HttpResponse.json(response);
    },
  ),

  // POST /api/v1/schedule/jobs/:id/check-conflicts
  http.post<{ id: string }>(
    "/api/v1/schedule/jobs/:id/check-conflicts",
    async ({ request }) => {
      const body = (await request.json()) as {
        tech_id: string | null;
        scheduled_start_at: string;
        scheduled_end_at: string;
      };

      // Simulate overlap conflict when moving to tech-1 9-11 AM (job-1 is there)
      const hasOverlap =
        body.tech_id === "tech-1" && body.scheduled_start_at.includes("T09:");

      const response: CheckConflictsResponse = hasOverlap
        ? {
            conflicts: [
              {
                conflict_class: "overlap",
                severity: "warn",
                detail: {
                  overlapping_job_id: "job-1",
                  overlapping_job_title: "Panel upgrade — 200A service",
                },
                affected_job_id: "job-1",
                suggested_resolution:
                  "Move the existing job or choose a different time slot.",
              },
            ],
            has_blocking_conflicts: false, // MVP: all warn-only per §13.4
          }
        : {
            conflicts: [],
            has_blocking_conflicts: false,
          };

      return HttpResponse.json(response);
    },
  ),

  // POST /api/v1/schedule/drive-times
  http.post("/api/v1/schedule/drive-times", async ({ request }) => {
    const body = (await request.json()) as {
      segments: Array<{ from_job_id: string; to_job_id: string }>;
      date: string;
    };

    const response: DriveTimeResponse = {
      segments: body.segments.map((seg) => ({
        from_job_id: seg.from_job_id,
        to_job_id: seg.to_job_id,
        drive_time_seconds: 1200, // 20 min default
        drive_distance_meters: 8000,
        is_feasible: true,
        cached: false,
      })),
    };

    return HttpResponse.json(response);
  }),

  // GET /api/v1/schedule/availability/:user_id
  http.get<{ user_id: string }>(
    "/api/v1/schedule/availability/:user_id",
    ({ params }) => {
      const response: TechAvailability = {
        user_id: params.user_id,
        date: new Date().toISOString().split("T")[0] ?? "",
        work_start: "07:00",
        work_end: "17:00",
        pto_periods: [],
      };

      return HttpResponse.json(response);
    },
  ),

  // GET /api/v1/schedule/board/stream (SSE — returns mock event stream)
  // Note: Native EventSource cannot be intercepted by standard MSW handlers.
  // For unit tests, use the eventSourceFactory injection on useSseChannel.
  // This handler returns a minimal SSE response for integration tests.
  http.get("/api/v1/schedule/board/stream", () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        // Send a keepalive comment immediately
        controller.enqueue(encoder.encode(": keepalive\n\n"));
        // Send one mock event
        controller.enqueue(
          encoder.encode(
            `event: job_scheduled\ndata: ${JSON.stringify({ event_type: "job_scheduled", job_id: "job-1" })}\n\n`,
          ),
        );
        // Keep stream open (never close in mock)
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }),
];
