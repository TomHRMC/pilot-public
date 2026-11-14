/**
 * MSW handlers — Help + Feedback — FE-B16
 *
 * Location: apps/web/src/mocks/handlers/helpHandlers.ts
 *
 * All help and feedback endpoints with fixtures for:
 * - Normal AI response (RAG hit)
 * - Knowledge boundary response (empty retrieved_article_ids)
 * - Contextual opener (context_payload present)
 * - Session list, session detail, session delete
 * - Inline session feedback
 * - Article delivery
 * - Feedback form (success + 400 error)
 *
 * RULE 5: MSW handlers created BEFORE any component.
 */

import { http, HttpResponse } from "msw";
import {
  MOCK_CHAT_RESPONSE_NORMAL,
  MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY,
  MOCK_CHAT_RESPONSE_WITH_CONTEXT,
  MOCK_SESSION_LIST_RESPONSE,
  MOCK_SESSION_DETAIL,
  MOCK_SESSION_FEEDBACK_RESOLVED,
  MOCK_SESSION_FEEDBACK_ESCALATED,
  MOCK_SESSION_DELETE_RESPONSE,
  MOCK_ARTICLE_RESPONSE,
  MOCK_FEEDBACK_SUBMIT_RESPONSE,
} from "../fixtures/helpFixtures";

// ── POST /api/v1/help/chat ──────────────────────────────────────────────────

export const helpChatNormalHandler = http.post(
  `*/api/v1/help/chat`,
  async ({ request }) => {
    const body = (await request.json()) as {
      message?: string;
      context_payload?: unknown;
      session_id?: string;
    };

    // Context payload present → return contextual response
    if (body.context_payload) {
      return HttpResponse.json(MOCK_CHAT_RESPONSE_WITH_CONTEXT, {
        status: 200,
      });
    }

    // Trigger knowledge boundary for specific message text
    if (
      body.message &&
      (body.message.toLowerCase().includes("unknown") ||
        body.message.toLowerCase().includes("no docs"))
    ) {
      return HttpResponse.json(MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY, {
        status: 200,
      });
    }

    return HttpResponse.json(MOCK_CHAT_RESPONSE_NORMAL, { status: 200 });
  },
);

export const helpChatBoundaryHandler = http.post(
  `*/api/v1/help/chat`,
  async () => {
    return HttpResponse.json(MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY, {
      status: 200,
    });
  },
);

export const helpChatServiceErrorHandler = http.post(
  `*/api/v1/help/chat`,
  async () => {
    return HttpResponse.json(
      { detail: "AI service temporarily unavailable" },
      { status: 503 },
    );
  },
);

// ── GET /api/v1/help/sessions ──────────────────────────────────────────────

export const helpSessionsListHandler = http.get(
  `*/api/v1/help/sessions`,
  () => {
    return HttpResponse.json(MOCK_SESSION_LIST_RESPONSE, { status: 200 });
  },
);

// ── GET /api/v1/help/sessions/test (test endpoint) ─────────────────────────

export const helpSessionsTestHandler = http.get(
  `*/api/v1/help/sessions/test`,
  () => {
    return HttpResponse.json(MOCK_SESSION_LIST_RESPONSE, { status: 200 });
  },
);

// ── GET /api/v1/help/sessions/:session_id ─────────────────────────────────

export const helpSessionDetailHandler = http.get(
  `*/api/v1/help/sessions/:session_id`,
  ({ params }) => {
    const { session_id } = params;
    if (session_id === "session-today-001") {
      return HttpResponse.json(MOCK_SESSION_DETAIL, { status: 200 });
    }
    return HttpResponse.json({ detail: "Session not found" }, { status: 404 });
  },
);

// ── DELETE /api/v1/help/sessions/:session_id ──────────────────────────────

export const helpSessionDeleteHandler = http.delete(
  `*/api/v1/help/sessions/:session_id`,
  ({ params }) => {
    return HttpResponse.json(
      {
        ...MOCK_SESSION_DELETE_RESPONSE,
        session_id: params.session_id as string,
      },
      { status: 200 },
    );
  },
);

// ── POST /api/v1/help/sessions/:session_id/feedback ───────────────────────

export const helpSessionFeedbackHandler = http.post(
  `*/api/v1/help/sessions/:session_id/feedback`,
  async ({ request, params }) => {
    const body = (await request.json()) as { signal: string };
    const response =
      body.signal === "resolved"
        ? MOCK_SESSION_FEEDBACK_RESOLVED
        : MOCK_SESSION_FEEDBACK_ESCALATED;
    return HttpResponse.json(
      { ...response, session_id: params.session_id as string },
      { status: 200 },
    );
  },
);

// ── GET /api/v1/help/articles/:article_id ─────────────────────────────────

export const helpArticleHandler = http.get(
  `*/api/v1/help/articles/:article_id`,
  ({ params }) => {
    return HttpResponse.json(
      { ...MOCK_ARTICLE_RESPONSE, article_id: params.article_id as string },
      { status: 200 },
    );
  },
);

// ── POST /api/v1/feedback ─────────────────────────────────────────────────

export const feedbackSubmitHandler = http.post(
  `*/api/v1/feedback`,
  async ({ request }) => {
    const body = (await request.json()) as { body?: string };
    // Simulate 400 for very short body
    if (!body.body || body.body.length < 1) {
      return HttpResponse.json({ detail: "Body is required" }, { status: 400 });
    }
    return HttpResponse.json(MOCK_FEEDBACK_SUBMIT_RESPONSE, { status: 201 });
  },
);

export const feedbackSubmitErrorHandler = http.post(
  `*/api/v1/feedback`,
  async () => {
    return HttpResponse.json(
      { detail: "Internal server error" },
      { status: 500 },
    );
  },
);

// ── Aggregated handlers array ──────────────────────────────────────────────

export const helpHandlers = [
  helpChatNormalHandler,
  helpSessionsListHandler,
  helpSessionsTestHandler,
  helpSessionDetailHandler,
  helpSessionDeleteHandler,
  helpSessionFeedbackHandler,
  helpArticleHandler,
  feedbackSubmitHandler,
];
