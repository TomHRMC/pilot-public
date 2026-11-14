/**
 * QuickBooks Conflict MSW handlers — web
 *
 * Location: apps/web/src/mocks/handlers/qbConflictHandlers.ts
 *
 * Established FE-B9. Consumed by:
 *   - MSW browser dev worker (via handlers/index.ts)
 *   - Integration tests (apps/web/__tests__/batch_fe_b9/)
 *
 * Endpoints covered:
 *   GET  /api/v1/integrations/quickbooks/conflicts               (list — all entity types)
 *   GET  /api/v1/integrations/quickbooks/conflicts/:id           (detail — customer/quote/invoice/expense)
 *   POST /api/v1/integrations/quickbooks/conflicts/:id/resolve   (success / 409-auto-recovery)
 *   GET  /api/v1/integrations/quickbooks/conflicts/stream        (SSE)
 *
 * RULE 3: No voice resolution UI — QB is read-only via voice.
 * RULE 8: MSW-first — handlers before any surface component.
 */

import { http, HttpResponse } from "msw";
import {
  qbConflictQueueList,
  customerConflictDetail,
  quoteConflictDetail,
  invoiceConflictDetail,
  expenseConflictDetail,
  qbConflict409AutoRecovery,
} from "../../features/quickbooks-conflict/mocks/qbConflictFixtures";

// ─── Handler: GET /api/v1/integrations/quickbooks/conflicts ──────────────────

const qbConflictListHandler = http.get(
  "/api/v1/integrations/quickbooks/conflicts",
  ({ request }) => {
    const url = new URL(request.url);
    const entityType = url.searchParams.get("entity_type");
    const status = url.searchParams.get("status");
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);

    // Empty state variant
    if (url.searchParams.get("_variant") === "empty") {
      return HttpResponse.json({
        conflicts: [],
        next_cursor: null,
        total_pending: 0,
      });
    }

    let conflicts = [...qbConflictQueueList];

    // Filter by entity_type if provided
    if (entityType) {
      conflicts = conflicts.filter((c) => c.entityType === entityType);
    }

    // Filter resolved if status="pending"
    if (status === "pending") {
      conflicts = conflicts.filter((c) => c.resolution === null);
    }

    conflicts = conflicts.slice(0, limit);

    return HttpResponse.json({
      conflicts,
      next_cursor: null,
      total_pending: qbConflictQueueList.filter((c) => c.resolution === null)
        .length,
    });
  },
);

// ─── Handler: GET /api/v1/integrations/quickbooks/conflicts/:id ──────────────

const qbConflictDetailHandler = http.get(
  "/api/v1/integrations/quickbooks/conflicts/:id",
  ({ params }) => {
    const { id } = params;

    // Route to correct fixture by ID
    if (id === "qb-quote-001") {
      return HttpResponse.json(quoteConflictDetail);
    }

    if (id === "qb-invoice-001") {
      return HttpResponse.json(invoiceConflictDetail);
    }

    if (id === "qb-expense-001") {
      return HttpResponse.json(expenseConflictDetail);
    }

    if (id === "qb-not-found") {
      return new HttpResponse(null, { status: 404 });
    }

    // Default: customer conflict (qb-cust-001 or any unknown id)
    return HttpResponse.json({
      ...customerConflictDetail,
      id: typeof id === "string" ? id : customerConflictDetail.id,
    });
  },
);

// ─── Handler: POST /api/v1/integrations/quickbooks/conflicts/:id/resolve ─────

const qbConflictResolveHandler = http.post(
  "/api/v1/integrations/quickbooks/conflicts/:id/resolve",
  async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as {
      resolution: string;
      expected_pilot_modified_at: string;
      expected_external_modified_at: string;
      _variant?: string;
    };

    // 409 auto-recovery test scenario
    if (body._variant === "409_auto_recovery") {
      return HttpResponse.json(qbConflict409AutoRecovery, { status: 409 });
    }

    // Success response
    return HttpResponse.json({
      id: typeof id === "string" ? id : "qb-cust-001",
      resolution: body.resolution,
      resolved_at: new Date().toISOString(),
      resolved_by_user_id: "user-mike",
    });
  },
);

// ─── Handler: GET /api/v1/integrations/quickbooks/conflicts/stream (SSE) ─────

const qbConflictSseHandler = http.get(
  "/api/v1/integrations/quickbooks/conflicts/stream",
  () => {
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        // Initial heartbeat
        controller.enqueue(encoder.encode(": heartbeat\n\n"));

        // Emit conflict_detected event (tests SSE → cache invalidation path)
        setTimeout(() => {
          const event = JSON.stringify({
            type: "conflict_detected",
            conflict_id: "qb-invoice-001",
            entity_type: "invoice",
            entity_id: "inv-5501",
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

export const qbConflictHandlers = [
  qbConflictListHandler,
  qbConflictDetailHandler,
  qbConflictResolveHandler,
  qbConflictSseHandler,
];

/**
 * Variant override handlers for integration tests.
 * Use with server.use() in beforeEach / it blocks.
 */
export const qbConflictHandlerVariants = {
  /** Empty conflicts list */
  emptyList: http.get("/api/v1/integrations/quickbooks/conflicts", () =>
    HttpResponse.json({ conflicts: [], next_cursor: null, total_pending: 0 }),
  ),

  /** Invoice detail (QB master — renders QB on left) */
  invoiceDetail: http.get("/api/v1/integrations/quickbooks/conflicts/:id", () =>
    HttpResponse.json(invoiceConflictDetail),
  ),

  /** Quote detail (Pilot master — renders Pilot on left) */
  quoteDetail: http.get("/api/v1/integrations/quickbooks/conflicts/:id", () =>
    HttpResponse.json(quoteConflictDetail),
  ),

  /** Customer detail */
  customerDetail: http.get(
    "/api/v1/integrations/quickbooks/conflicts/:id",
    () => HttpResponse.json(customerConflictDetail),
  ),

  /** Expense detail */
  expenseDetail: http.get("/api/v1/integrations/quickbooks/conflicts/:id", () =>
    HttpResponse.json(expenseConflictDetail),
  ),

  /** 409 auto-recovery on resolve */
  resolveWith409AutoRecovery: http.post(
    "/api/v1/integrations/quickbooks/conflicts/:id/resolve",
    () => HttpResponse.json(qbConflict409AutoRecovery, { status: 409 }),
  ),
};
