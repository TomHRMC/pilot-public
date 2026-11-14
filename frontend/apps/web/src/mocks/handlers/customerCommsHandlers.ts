/**
 * customerCommsHandlers — MSW handlers for all SMS / Customer Comms endpoints
 *
 * Location: apps/web/src/mocks/handlers/customerCommsHandlers.ts
 * Used by: MSW browser worker (web) + integration tests
 *
 * Covers:
 *   GET  /api/v1/customers/:customerId/communication-history
 *   GET  /api/v1/customers/:customerId/threads  [MSW bridge — backend TODO]
 *   GET  /api/v1/dashboard/widgets/recent-customer-messages
 *   GET  /api/v1/communications/unrouted
 *   POST /api/v1/communications/unrouted/:id/assign
 *   GET  /api/v1/customers/:customerId/comms/stream  (SSE)
 *   GET  /api/v1/dashboard/stream  (SSE)
 *
 * STEP 1 gate: All endpoints respond; fixtures compile without type casting.
 */

import { http, HttpResponse } from "msw";
import {
  CUSTOMER_COMMS_HISTORY,
  CUSTOMER_COMMS_HISTORY_OPTED_OUT,
  RECENT_MESSAGES,
  UNROUTED_MESSAGES,
  THREAD_1,
  THREAD_2,
  THREAD_3_OPTED_OUT,
} from "../../features/customer-comms/mocks/customerCommsFixtures";

const BASE = "/api/v1";

// ── Customer comms history ────────────────────────────────────────────────────

export const getCustomerCommsHistory = http.get(
  `${BASE}/customers/:customerId/communication-history`,
  ({ params }) => {
    const { customerId } = params as { customerId: string };

    // customer-003 = opted out
    if (customerId === "customer-003") {
      return HttpResponse.json(CUSTOMER_COMMS_HISTORY_OPTED_OUT);
    }

    return HttpResponse.json(CUSTOMER_COMMS_HISTORY);
  },
);

// ── Customer SMS threads (MSW bridge — backend endpoint TODO) ─────────────────
// TODO [COMPANION-BE]: Backend must implement GET /api/v1/customers/{id}/threads
// returning { threads: SmsThread[], total: number } so SD-02 seeded messages
// are visible from the customer comms tab when navigating from the inbox.

export const getCustomerSmsThreads = http.get(
  `${BASE}/customers/:customerId/threads`,
  ({ params }) => {
    const { customerId } = params as { customerId: string };

    const allThreads = [THREAD_1, THREAD_2, THREAD_3_OPTED_OUT];
    const threads = allThreads.filter((t) => t.customer_id === customerId);

    return HttpResponse.json({
      threads,
      total: threads.length,
    });
  },
);

// ── Dashboard widget ──────────────────────────────────────────────────────────

export const getRecentCustomerMessages = http.get(
  `${BASE}/dashboard/widgets/recent-customer-messages`,
  ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") ?? "10", 10);

    return HttpResponse.json({
      messages: RECENT_MESSAGES.messages.slice(0, limit),
    });
  },
);

// ── Unrouted messages ─────────────────────────────────────────────────────────

export const getUnroutedMessages = http.get(
  `${BASE}/communications/unrouted`,
  () => {
    return HttpResponse.json({
      messages: UNROUTED_MESSAGES,
      next_cursor: null,
      total_count: UNROUTED_MESSAGES.length,
    });
  },
);

export const postAssignUnrouted = http.post(
  `${BASE}/communications/unrouted/:id/assign`,
  ({ params }) => {
    const { id } = params as { id: string };

    if (!UNROUTED_MESSAGES.find((m) => m.unrouted_id === id)) {
      return HttpResponse.json(
        { detail: "unrouted_message_not_found" },
        { status: 404 },
      );
    }

    return HttpResponse.json({
      thread_id: `thread-new-${id}`,
      message_id: `msg-new-${id}`,
      customer_name: "Assigned Customer",
      tech_name: "Mike Johnson",
    });
  },
);

// ── SSE channels (web) ────────────────────────────────────────────────────────

export const getCustomerCommsSseStream = http.get(
  `${BASE}/customers/:customerId/comms/stream`,
  () => {
    // SSE — returns an event stream
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        // Emit one test event then close
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "customer_message_received",
              data: {
                thread_id: "thread-002",
                message_id: "msg-sse-001",
                direction: "inbound",
                body_preview: "New inbound message via SSE",
                received_at: new Date().toISOString(),
              },
            })}\n\n`,
          ),
        );
        controller.close();
      },
    });

    return new HttpResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  },
);

export const getDashboardSseStream = http.get(
  `${BASE}/dashboard/stream`,
  () => {
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "customer_message_received",
              data: {
                thread_id: "thread-001",
                message_id: "msg-sse-002",
                direction: "inbound",
                body_preview: "Dashboard SSE test message",
                received_at: new Date().toISOString(),
              },
            })}\n\n`,
          ),
        );
        controller.close();
      },
    });

    return new HttpResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  },
);

// ── Handler array export ──────────────────────────────────────────────────────

export const customerCommsHandlers = [
  getCustomerCommsHistory,
  getCustomerSmsThreads,
  getRecentCustomerMessages,
  getUnroutedMessages,
  postAssignUnrouted,
  getCustomerCommsSseStream,
  getDashboardSseStream,
];
