/**
 * Field Issues MSW handlers — web
 *
 * Location: apps/web/src/mocks/handlers/fieldIssuesHandlers.ts
 *
 * Established FE-B9. Consumed by:
 *   - MSW browser dev worker (via handlers/index.ts)
 *   - Integration tests (apps/web/__tests__/batch_fe_b9/)
 *
 * Endpoints covered:
 *   GET  /api/v1/owner/field-issues             (list — pending/all + filter variants)
 *   GET  /api/v1/owner/field-issues/summary     (mobile badge count)
 *   GET  /api/v1/owner/field-issues/:id         (detail — mm / del-mod / perm-revoked)
 *   POST /api/v1/owner/field-issues/:id/resolve (success / 409-server_changed / 409-auto_recovered / 409-stale)
 *   GET  /api/v1/owner/mobile-sync-escalations/stream      (SSE)
 *
 * RULE 8 — MSW-first: all handlers written before any surface component.
 */

import { http, HttpResponse } from "msw";
import {
  fieldIssueQueueList,
  timeEntryModifiedModifiedDetail,
  expenseDeletedModifiedDetail,
  permissionRevokedDetail,
  fieldIssue409ServerChanged,
  fieldIssue409AutoRecovered,
  fieldIssue409Stale,
  fieldIssuesSummaryFixture,
  fieldIssuesSummaryEmptyFixture,
} from "../../features/field-issues/mocks/fieldIssuesFixtures";

// ─── Handler: GET /api/v1/owner/field-issues ──────────────────────────────────

const fieldIssuesListHandler = http.get(
  "/api/v1/owner/mobile-sync-escalations",
  ({ request }) => {
    const url = new URL(request.url);
    // API uses 'escalation_status', not 'status'
    const status = url.searchParams.get("escalation_status");
    const operationType = url.searchParams.get("operation_type");
    const limit = parseInt(url.searchParams.get("limit") ?? "25", 10);

    // Empty state variant
    if (url.searchParams.get("_variant") === "empty") {
      return HttpResponse.json({
        items: [],
        next_cursor: null,
        total_pending: 0,
      });
    }

    // Filter by operation type if provided
    let issues = [...fieldIssueQueueList];
    if (operationType) {
      issues = issues.filter((i) => i.operationType === operationType);
    }
    // Filter by status if provided and not 'all'
    if (status && status !== "all") {
      issues = issues.filter((i) => i.status === status);
    }

    issues = issues.slice(0, limit);

    // Return EscalationListItem shape
    return HttpResponse.json({
      items: issues.map((i) => ({
        id: i.id,
        status: i.status,
        operation_type: i.operationType,
        originating_user_id: i.techId,
        originating_user_name: i.techName,
        escalated_at: i.escalatedAt,
        escalation_reason: i.explainerSummary,
        escalation_reason_explainer: i.explainerSummary,
        conflict_severity: i.conflictType,
      })),
      next_cursor: null,
      total_pending: fieldIssueQueueList.filter((i) => i.status === "pending")
        .length,
    });
  },
);

// ─── Handler: GET /api/v1/owner/field-issues/summary (mobile) ────────────────

// NOTE: This must come BEFORE the :id handler to avoid route collision
const fieldIssuesSummaryHandler = http.get(
  "/api/v1/owner/field-issues/summary",
  ({ request }) => {
    const url = new URL(request.url);
    const variant = url.searchParams.get("_variant");

    if (variant === "empty") {
      return HttpResponse.json(fieldIssuesSummaryEmptyFixture);
    }

    return HttpResponse.json(fieldIssuesSummaryFixture);
  },
);

// ─── Handler: GET /api/v1/owner/field-issues/:id ─────────────────────────────

const fieldIssueDetailHandler = http.get(
  "/api/v1/owner/mobile-sync-escalations/:id",
  ({ params }) => {
    const { id } = params;

    // Expense deleted_modified conflict
    if (id === "fi-expense-001") {
      return HttpResponse.json(expenseDeletedModifiedDetail);
    }

    // Permission revoked conflict
    if (id === "fi-perm-001") {
      return HttpResponse.json(permissionRevokedDetail);
    }

    // 404 test
    if (id === "fi-not-found") {
      return new HttpResponse(null, { status: 404 });
    }

    // Default: time_entry modified_modified (fi-time-001 or any other id)
    return HttpResponse.json({
      ...timeEntryModifiedModifiedDetail,
      id: typeof id === "string" ? id : timeEntryModifiedModifiedDetail.id,
    });
  },
);

// ─── Handler: POST /api/v1/owner/field-issues/:id/resolve ────────────────────

const fieldIssueResolveHandler = http.post(
  "/api/v1/owner/mobile-sync-escalations/:id/resolve",
  async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as {
      resolution: string;
      expected_server_state_hash: string;
      _variant?: string;
    };

    // Test scenario via _variant field
    if (body._variant === "409_server_changed") {
      return HttpResponse.json(fieldIssue409ServerChanged, { status: 409 });
    }

    if (body._variant === "409_auto_recovered") {
      return HttpResponse.json(fieldIssue409AutoRecovered, { status: 409 });
    }

    if (body._variant === "409_stale") {
      return HttpResponse.json(fieldIssue409Stale, { status: 409 });
    }

    // Success response
    return HttpResponse.json({
      id: typeof id === "string" ? id : "fi-time-001",
      resolution: body.resolution,
      resolved_at: new Date().toISOString(),
      resolved_by_user_id: "user-mike",
    });
  },
);

// ─── Handler: GET /api/v1/owner/mobile-sync-escalations/stream (SSE) ─────────────────────

const fieldIssuesSseHandler = http.get(
  "/api/v1/owner/mobile-sync-escalations/stream",
  () => {
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        // Initial heartbeat
        controller.enqueue(encoder.encode(": heartbeat\n\n"));

        // Emit escalation_created after 500ms (tests the SSE invalidation path)
        setTimeout(() => {
          const event = JSON.stringify({
            type: "escalation_created",
            issue_id: "fi-time-001",
            tech_id: "tech-jake-001",
            operation_type: "time_entry",
          });
          controller.enqueue(
            encoder.encode(`event: escalation_created\ndata: ${event}\n\n`),
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

export const fieldIssuesHandlers = [
  fieldIssuesSummaryHandler, // Must be before :id handler
  fieldIssuesSseHandler, // Must be before :id handler to avoid route collision
  fieldIssuesListHandler,
  fieldIssueDetailHandler,
  fieldIssueResolveHandler,
];

/**
 * Variant override handlers for integration tests.
 * Use with server.use() in beforeEach / it blocks.
 */
export const fieldIssuesHandlerVariants = {
  /** Empty field issues list */
  emptyList: http.get("/api/v1/owner/mobile-sync-escalations", () =>
    HttpResponse.json({ items: [], next_cursor: null, total_pending: 0 }),
  ),

  /** Deletion conflict detail */
  deletedModifiedDetail: http.get(
    "/api/v1/owner/mobile-sync-escalations/:id",
    () => HttpResponse.json(expenseDeletedModifiedDetail),
  ),

  /** Permission revoked detail */
  permissionRevokedDetail: http.get(
    "/api/v1/owner/mobile-sync-escalations/:id",
    () => HttpResponse.json(permissionRevokedDetail),
  ),

  /** 409 server_changed on resolve */
  resolveWith409ServerChanged: http.post(
    "/api/v1/owner/mobile-sync-escalations/:id/resolve",
    () => HttpResponse.json(fieldIssue409ServerChanged, { status: 409 }),
  ),

  /** 409 auto_recovered on resolve */
  resolveWith409AutoRecovered: http.post(
    "/api/v1/owner/mobile-sync-escalations/:id/resolve",
    () => HttpResponse.json(fieldIssue409AutoRecovered, { status: 409 }),
  ),

  /** 409 stale on resolve */
  resolveWith409Stale: http.post(
    "/api/v1/owner/mobile-sync-escalations/:id/resolve",
    () => HttpResponse.json(fieldIssue409Stale, { status: 409 }),
  ),

  /** Empty summary (mobile — no pending) */
  emptySummary: http.get("/api/v1/owner/field-issues/summary", () =>
    HttpResponse.json(fieldIssuesSummaryEmptyFixture),
  ),
};
