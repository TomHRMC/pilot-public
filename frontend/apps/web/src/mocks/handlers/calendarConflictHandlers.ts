/**
 * Calendar conflict MSW handlers — web
 *
 * Location: apps/web/src/mocks/handlers/calendarConflictHandlers.ts
 *
 * Established FE-B8. Consumed by:
 *   - MSW browser dev worker (via handlers/index.ts)
 *   - Integration tests (apps/web/__tests__/batch_fe_b8/)
 *
 * Endpoints covered:
 *   GET  /api/v1/integrations/calendar/conflicts
 *   GET  /api/v1/integrations/calendar/conflicts/:id
 *   POST /api/v1/integrations/calendar/conflicts/:id/resolve
 *   GET  /api/v1/integrations/calendar/status
 *   GET  /api/v1/integrations/calendar/conflicts/stream  (SSE)
 *
 * To activate a variant in tests, use server.use() to override the default handler.
 */

import { http, HttpResponse } from "msw";
import {
  conflictListItemFixtures,
  deletionConflictListItems,
  modifiedModifiedDetailFixture,
  deletedModifiedDetailFixture,
  modifiedDeletedDetailFixture,
  resolvedConflictDetailFixture,
  stalenesErrorBody,
  connectedStatusFixture,
  errorStatusFixture,
  disconnectedStatusFixture,
} from "../../features/calendar-conflict/mocks/calendarConflictFixtures";

// ─── State tracking for test scenario control ─────────────────────────────────

// Tests can flip these via server.use() override handlers
type ListVariant = "default" | "empty" | "deletion";
type StatusVariant = "connected" | "error" | "disconnected";

// ─── Handler: GET /api/v1/integrations/calendar/conflicts ──────────────────

const conflictListDefaultHandler = http.get(
  "/api/v1/integrations/calendar/conflicts",
  ({ request }) => {
    const url = new URL(request.url);
    const variant = url.searchParams.get("_variant") as ListVariant | null;

    if (variant === "empty") {
      return HttpResponse.json({
        conflicts: [],
        next_cursor: null,
        total_pending: 0,
      });
    }

    if (variant === "deletion") {
      return HttpResponse.json({
        conflicts: deletionConflictListItems,
        next_cursor: null,
        total_pending: deletionConflictListItems.length,
      });
    }

    // Default: 3 modified_modified conflicts (urgency-sorted)
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);
    const conflicts = conflictListItemFixtures.slice(0, limit);

    return HttpResponse.json({
      conflicts,
      next_cursor: null,
      total_pending: conflictListItemFixtures.length,
    });
  },
);

// ─── Handler: GET /api/v1/integrations/calendar/conflicts/:id ─────────────

const conflictDetailDefaultHandler = http.get(
  "/api/v1/integrations/calendar/conflicts/:id",
  ({ params }) => {
    const { id } = params;

    if (id === "conflict-resolved-1") {
      return HttpResponse.json(resolvedConflictDetailFixture);
    }

    if (id === "conflict-dm-1") {
      return HttpResponse.json(deletedModifiedDetailFixture);
    }

    if (id === "conflict-md-1") {
      return HttpResponse.json(modifiedDeletedDetailFixture);
    }

    if (id === "conflict-404") {
      return new HttpResponse(null, { status: 404 });
    }

    // Default: modified_modified with 5 field diffs
    return HttpResponse.json({
      ...modifiedModifiedDetailFixture,
      id: typeof id === "string" ? id : modifiedModifiedDetailFixture.id,
    });
  },
);

// ─── Handler: POST /api/v1/integrations/calendar/conflicts/:id/resolve ────

const conflictResolveDefaultHandler = http.post(
  "/api/v1/integrations/calendar/conflicts/:id/resolve",
  async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as {
      resolution: string;
      expected_pilot_modified_at: string;
      expected_external_modified_at: string;
      _variant?: string;
    };

    // Allow test to trigger 409 via _variant field in body
    if (body._variant === "409") {
      return HttpResponse.json(stalenesErrorBody, { status: 409 });
    }

    return HttpResponse.json({
      id: typeof id === "string" ? id : "conflict-mm-1",
      resolution: body.resolution,
      resolved_at: new Date().toISOString(),
      resolved_by_user_id: "user-mike",
    });
  },
);

// ─── Handler: GET /api/v1/integrations/calendar/status ────────────────────

const calendarStatusDefaultHandler = http.get(
  "/api/v1/integrations/calendar/status",
  ({ request }) => {
    const url = new URL(request.url);
    const variant = url.searchParams.get("_variant") as StatusVariant | null;

    if (variant === "error") {
      return HttpResponse.json(errorStatusFixture);
    }

    if (variant === "disconnected") {
      return HttpResponse.json(disconnectedStatusFixture);
    }

    // Default: connected with pending conflicts
    return HttpResponse.json(connectedStatusFixture);
  },
);

// ─── Handler: GET /api/v1/integrations/calendar/conflicts/stream (SSE) ───

const calendarSseStreamHandler = http.get(
  "/api/v1/integrations/calendar/conflicts/stream",
  () => {
    // Simulate SSE stream — emits one conflict_detected event after open
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        // Initial heartbeat
        controller.enqueue(encoder.encode(": heartbeat\n\n"));

        // Emit a conflict_detected event (used in SSE invalidation tests)
        setTimeout(() => {
          const event = JSON.stringify({
            type: "conflict_detected",
            conflict_id: "conflict-mm-1",
            job_id: "job-1",
          });
          controller.enqueue(
            encoder.encode(`event: conflict_detected\ndata: ${event}\n\n`),
          );
        }, 500);
      },
    });

    return new HttpResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  },
);

// ─── Exports ──────────────────────────────────────────────────────────────────

export const calendarConflictHandlers = [
  conflictListDefaultHandler,
  conflictDetailDefaultHandler,
  conflictResolveDefaultHandler,
  calendarStatusDefaultHandler,
  calendarSseStreamHandler,
];

/**
 * Variant override handlers for integration tests.
 * Use with server.use() in beforeEach / it blocks.
 */
export const calendarConflictHandlerVariants = {
  /** Empty conflict list */
  emptyConflictList: http.get("/api/v1/integrations/calendar/conflicts", () =>
    HttpResponse.json({
      conflicts: [],
      next_cursor: null,
      total_pending: 0,
    }),
  ),

  /** Deletion conflicts only */
  deletionConflictList: http.get(
    "/api/v1/integrations/calendar/conflicts",
    () =>
      HttpResponse.json({
        conflicts: deletionConflictListItems,
        next_cursor: null,
        total_pending: deletionConflictListItems.length,
      }),
  ),

  /** deleted_modified detail */
  deletedModifiedDetail: http.get(
    "/api/v1/integrations/calendar/conflicts/:id",
    () => HttpResponse.json(deletedModifiedDetailFixture),
  ),

  /** modified_deleted detail */
  modifiedDeletedDetail: http.get(
    "/api/v1/integrations/calendar/conflicts/:id",
    () => HttpResponse.json(modifiedDeletedDetailFixture),
  ),

  /** Already-resolved conflict */
  resolvedConflictDetail: http.get(
    "/api/v1/integrations/calendar/conflicts/:id",
    () => HttpResponse.json(resolvedConflictDetailFixture),
  ),

  /** 409 staleness on resolve */
  resolveWith409: http.post(
    "/api/v1/integrations/calendar/conflicts/:id/resolve",
    () => HttpResponse.json(stalenesErrorBody, { status: 409 }),
  ),

  /** Error connection status */
  errorConnectionStatus: http.get("/api/v1/integrations/calendar/status", () =>
    HttpResponse.json(errorStatusFixture),
  ),

  /** Disconnected status */
  disconnectedStatus: http.get("/api/v1/integrations/calendar/status", () =>
    HttpResponse.json(disconnectedStatusFixture),
  ),
};
