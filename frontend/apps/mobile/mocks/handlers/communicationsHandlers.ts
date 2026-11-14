/**
 * communicationsHandlers — MSW handlers for mobile SMS endpoints
 *
 * Location: apps/mobile/mocks/handlers/communicationsHandlers.ts
 * Used by: MSW in mobile integration tests for FE-B10
 *
 * Covers (per design doc G.2):
 *   GET  /api/v1/mobile/inbox/customer-threads
 *   GET  /api/v1/communications/threads/:threadId/messages
 *   POST /api/v1/communications/threads/:threadId/reply
 *   POST /api/v1/communications/threads/:threadId/mark-read
 *   GET  /api/v1/sms/quota
 *   GET  /api/v1/mobile/inbox/stream  (SSE)
 *
 * STEP 1 gate: All endpoints respond; fixtures compile without type casting.
 */

import { http, HttpResponse } from "msw";
import {
  THREAD_LIST_ITEMS,
  THREAD_1_MESSAGES,
  THREAD_1,
  QUOTA_NORMAL,
  QUOTA_WARNING_80,
  QUOTA_HARD_BLOCKED,
  QUOTA_SOFT_BLOCKED,
  QUOTA_OPTED_OUT,
  SSE_NEW_INBOUND_EVENT,
} from "../../features/customer-comms/mocks/customerCommsFixtures";
import type { SmsMessage } from "@pilot/ui";

const BASE = "*/api/v1";

// ── Mobile inbox thread list ──────────────────────────────────────────────────

export const getCustomerThreads = http.get(
  `${BASE}/mobile/inbox/customer-threads`,
  () => {
    return HttpResponse.json({
      threads: THREAD_LIST_ITEMS,
      next_cursor: null,
      total_unread: THREAD_LIST_ITEMS.reduce(
        (sum, t) => sum + t.unread_count,
        0,
      ),
    });
  },
);

// ── Thread messages (paginated) ───────────────────────────────────────────────

export const getThreadMessages = http.get(
  `${BASE}/communications/threads/:threadId/messages`,
  ({ params }) => {
    const { threadId } = params as { threadId: string };

    const messages = threadId === "thread-001" ? THREAD_1_MESSAGES : [];
    const thread = threadId === "thread-001" ? THREAD_1 : null;

    if (!thread) {
      return HttpResponse.json({ detail: "thread_not_found" }, { status: 404 });
    }

    return HttpResponse.json({
      messages,
      next_cursor: null,
      thread,
    });
  },
);

// ── Reply to thread ───────────────────────────────────────────────────────────

export const postThreadReply = http.post(
  `${BASE}/communications/threads/:threadId/reply`,
  async ({ params, request }) => {
    const { threadId } = params as { threadId: string };
    const body = (await request.json()) as {
      body?: string;
      composition_method?: string;
    };

    // Opted-out customer returns 422
    if (threadId === "thread-003") {
      return HttpResponse.json(
        { detail: "customer_opted_out" },
        { status: 422 },
      );
    }

    // Hard-cap returns 429
    if (body?.body?.includes("FORCE_HARD_CAP")) {
      return HttpResponse.json(
        { detail: "monthly_quota_reached" },
        { status: 429 },
      );
    }

    return HttpResponse.json({
      message_id: `msg-reply-${Date.now()}`,
      thread_id: threadId,
      status: "pending_send",
      segment_count: 1,
      sent_at: null,
    });
  },
);

// ── Delivery failure variant (used by integration tests via overrides) ─────────

export const postThreadReplyDeliveryFailure = http.post(
  `${BASE}/communications/threads/thread-fail/reply`,
  () => {
    return HttpResponse.json({
      message_id: "msg-fail-001",
      thread_id: "thread-fail",
      status: "failed",
      segment_count: 1,
      sent_at: null,
    });
  },
);

// ── Mark thread read ──────────────────────────────────────────────────────────

export const postMarkThreadRead = http.post(
  `${BASE}/communications/threads/:threadId/mark-read`,
  ({ params }) => {
    const { threadId } = params as { threadId: string };
    return HttpResponse.json({
      thread_id: threadId,
      marked_read_count: 2,
    });
  },
);

// ── SMS quota ─────────────────────────────────────────────────────────────────

/**
 * Default quota handler — returns based on customer_id param:
 *   customer-003 → opted_out
 *   ?quota=warning → 80% warning
 *   ?quota=hard → hard blocked
 *   ?quota=soft → soft blocked
 *   default → normal
 */
export const getSmsQuota = http.get(`${BASE}/sms/quota`, ({ request }) => {
  const url = new URL(request.url);
  const customerId = url.searchParams.get("customer_id");
  const quotaParam = url.searchParams.get("quota");

  if (customerId === "customer-003") {
    return HttpResponse.json(QUOTA_OPTED_OUT);
  }

  if (quotaParam === "warning") {
    return HttpResponse.json(QUOTA_WARNING_80);
  }
  if (quotaParam === "hard") {
    return HttpResponse.json(QUOTA_HARD_BLOCKED);
  }
  if (quotaParam === "soft") {
    return HttpResponse.json(QUOTA_SOFT_BLOCKED);
  }

  return HttpResponse.json(QUOTA_NORMAL);
});

// ── Mobile inbox SSE stream ───────────────────────────────────────────────────
// Note: Uses a string body instead of ReadableStream to avoid the
// asyncToGenerator leak in Jest workers (MSW v2 + Babel + jest-expo known issue).

export const getMobileInboxStream = http.get(
  `${BASE}/mobile/inbox/stream`,
  () => {
    return new HttpResponse(
      `data: ${JSON.stringify(SSE_NEW_INBOUND_EVENT)}\n\n`,
      {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
        },
      },
    );
  },
);

// ── Handler array export ──────────────────────────────────────────────────────

export const communicationsHandlers = [
  getCustomerThreads,
  getThreadMessages,
  postThreadReply,
  postThreadReplyDeliveryFailure,
  postMarkThreadRead,
  getSmsQuota,
  getMobileInboxStream,
];
