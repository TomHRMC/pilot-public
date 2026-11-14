/**
 * Help system MSW fixtures — FE-B16
 *
 * Location: apps/web/src/mocks/fixtures/helpFixtures.ts
 *
 * Provides deterministic test data for all help + feedback MSW handlers.
 */

import type {
  HelpChatResponse,
  HelpSessionListResponse,
  HelpSessionDetailResponse,
  HelpSessionFeedbackResponse,
  HelpSessionDeleteResponse,
  HelpArticleResponse,
  FeedbackSubmitResponse,
} from "../../features/help/types";

// ── Session fixtures ────────────────────────────────────────────────────────

export const MOCK_SESSION_TODAY = {
  session_id: "session-today-001",
  title: "How to connect QuickBooks Online",
  started_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
  last_activity_at: new Date(Date.now() - 1000 * 60 * 10).toISOString(), // 10 min ago
  message_count: 4,
  outcome: "resolved" as const,
};

export const MOCK_SESSION_LAST_7_DAYS = {
  session_id: "session-week-002",
  title: "Setting up margin buckets for electrical work",
  started_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(), // 3 days ago
  last_activity_at: new Date(
    Date.now() - 1000 * 60 * 60 * 24 * 3,
  ).toISOString(),
  message_count: 7,
  outcome: "escalated" as const,
};

export const MOCK_SESSION_OLDER = {
  session_id: "session-older-003",
  title: "Voice AI persona settings explained",
  started_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString(), // 2 weeks ago
  last_activity_at: new Date(
    Date.now() - 1000 * 60 * 60 * 24 * 14,
  ).toISOString(),
  message_count: 3,
  outcome: null,
};

export const MOCK_SESSION_LIST_RESPONSE: HelpSessionListResponse = {
  sessions: [MOCK_SESSION_TODAY, MOCK_SESSION_LAST_7_DAYS, MOCK_SESSION_OLDER],
  total: 3,
};

// ── Message fixtures ────────────────────────────────────────────────────────

export const MOCK_SESSION_DETAIL: HelpSessionDetailResponse = {
  session_id: "session-today-001",
  title: "How to connect QuickBooks Online",
  outcome: "resolved",
  messages: [
    {
      message_id: "msg-001",
      session_id: "session-today-001",
      role: "user",
      content: "How do I connect QuickBooks Online to Pilot?",
      created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      context_payload: null,
      retrieved_chunks: null,
      voice_used: false,
    },
    {
      message_id: "msg-002",
      session_id: "session-today-001",
      role: "assistant",
      content:
        "To connect QuickBooks Online to Pilot, go to **Settings → Integrations → QuickBooks** and click **Connect**. You'll be redirected to QuickBooks to authorize access. Once authorized, Pilot will sync your customers, invoices, and items automatically.",
      created_at: new Date(Date.now() - 1000 * 60 * 29).toISOString(),
      context_payload: null,
      retrieved_chunks: {
        count: 2,
        article_ids: ["article-qb-connect", "article-qb-sync"],
      },
      voice_used: false,
    },
    {
      message_id: "msg-003",
      session_id: "session-today-001",
      role: "user",
      content: "What data gets synced?",
      created_at: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
      context_payload: null,
      retrieved_chunks: null,
      voice_used: false,
    },
    {
      message_id: "msg-004",
      session_id: "session-today-001",
      role: "assistant",
      content:
        "Pilot syncs the following data with QuickBooks Online: **Customers** (contact info), **Invoices** (line items and totals), **Items/Services** (your service catalog). Estimates and quotes from Pilot become invoices in QuickBooks when accepted.",
      created_at: new Date(Date.now() - 1000 * 60 * 19).toISOString(),
      context_payload: null,
      retrieved_chunks: {
        count: 3,
        article_ids: [
          "article-qb-sync",
          "article-qb-invoices",
          "article-qb-items",
        ],
      },
      voice_used: false,
    },
  ],
};

// ── Chat response fixtures ──────────────────────────────────────────────────

export const MOCK_CHAT_RESPONSE_NORMAL: HelpChatResponse = {
  session_id: "session-today-001",
  message_id: "msg-resp-001",
  role: "assistant",
  content:
    "To connect QuickBooks Online to Pilot, go to **Settings → Integrations → QuickBooks** and click **Connect**. You'll be redirected to QuickBooks to authorize access.",
  retrieved_article_ids: ["article-qb-connect", "article-qb-sync"],
  session_title: "How to connect QuickBooks Online",
};

/** Knowledge boundary: AI has no documentation for this topic */
export const MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY: HelpChatResponse = {
  session_id: "session-today-001",
  message_id: "msg-resp-002",
  role: "assistant",
  content:
    "I don't have specific documentation on that topic in our help content. Our team may not have covered this area yet. You can send us feedback to let us know what you were looking for.",
  retrieved_article_ids: [],
  session_title: "Unknown topic query",
};

/** Contextual: response references context payload */
export const MOCK_CHAT_RESPONSE_WITH_CONTEXT: HelpChatResponse = {
  session_id: "session-ctx-003",
  message_id: "msg-resp-003",
  role: "assistant",
  content:
    "I can see you're on the QuickBooks integration settings page. The **Sync Direction** setting controls whether data flows one-way (Pilot → QuickBooks) or both ways. For most contractors, I recommend **One-way from Pilot** to keep QuickBooks as a read-only view.",
  retrieved_article_ids: ["article-qb-sync-direction"],
  session_title: "QuickBooks sync direction help",
};

// ── Session feedback fixtures ───────────────────────────────────────────────

export const MOCK_SESSION_FEEDBACK_RESOLVED: HelpSessionFeedbackResponse = {
  session_id: "session-today-001",
  outcome: "resolved",
};

export const MOCK_SESSION_FEEDBACK_ESCALATED: HelpSessionFeedbackResponse = {
  session_id: "session-today-001",
  outcome: "escalated",
};

// ── Session delete fixture ──────────────────────────────────────────────────

export const MOCK_SESSION_DELETE_RESPONSE: HelpSessionDeleteResponse = {
  message: "Session deleted",
  session_id: "session-today-001",
};

// ── Article fixture ─────────────────────────────────────────────────────────

export const MOCK_ARTICLE_RESPONSE: HelpArticleResponse = {
  article_id: "article-qb-connect",
  title: "Connecting QuickBooks Online to Pilot",
  category: "Integrations",
  content_markdown: `# Connecting QuickBooks Online to Pilot

## Prerequisites

Before connecting, ensure you have:
- An active QuickBooks Online account (Simple Start or higher)
- Admin access to your Pilot account

## Step-by-step instructions

1. Navigate to **Settings → Integrations → QuickBooks**
2. Click the **Connect to QuickBooks** button
3. You will be redirected to the Intuit authorization page
4. Sign in with your QuickBooks credentials and click **Authorize**
5. You will be redirected back to Pilot — the connection status should show **Connected**

## What gets synced?

| Data type | Direction | Frequency |
|-----------|-----------|-----------|
| Customers | Both ways | Real-time |
| Invoices | Pilot → QB | On save |
| Items/Services | QB → Pilot | On demand |

## Troubleshooting

If the connection fails, check that your QuickBooks account has API access enabled. Contact support if the issue persists.
`,
  audience: ["owner", "office_staff"],
  last_updated: "2026-04-15T00:00:00.000Z",
};

// ── Feedback submission fixtures ────────────────────────────────────────────

export const MOCK_FEEDBACK_SUBMIT_RESPONSE: FeedbackSubmitResponse = {
  submission_id: "feedback-sub-001",
  category: "general",
  submitted_at: new Date().toISOString(),
  confirmation_message:
    "Thanks for your feedback! Our team will review it shortly.",
};
