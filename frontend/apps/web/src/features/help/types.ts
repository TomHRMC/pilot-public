/**
 * Help feature types — FE-B16
 *
 * Location: apps/web/src/features/help/types.ts
 *
 * Web-local type aliases and form types for the help system.
 * Shared component types (HelpChatMessage, HelpChatSession, etc.)
 * are defined in packages/ui and re-exported here for convenience.
 */

// Re-export shared UI types for web consumers
export type {
  HelpContextPayload,
  HelpActionType,
  HelpAnchorProps,
  HelpChatMessage,
  HelpChatSession,
  HelpChatMessagesProps,
  HelpFollowUpAction,
  KnowledgeBoundaryMessageProps,
} from "@pilot/ui";

// ── API request/response types ────────────────────────────────────────────

export interface HelpChatRequest {
  session_id?: string;
  message: string;
  context_payload?: import("@pilot/ui").HelpContextPayload;
}

export interface HelpChatResponse {
  session_id: string;
  message_id: string;
  role: "assistant";
  content: string;
  retrieved_article_ids: string[];
  session_title: string | null;
}

export interface HelpSessionSummary {
  session_id: string;
  title: string | null;
  started_at: string;
  last_activity_at: string;
  message_count: number;
  outcome: "resolved" | "escalated" | "abandoned" | null;
}

export interface HelpSessionListResponse {
  sessions: HelpSessionSummary[];
  total: number;
}

export interface HelpMessageDetail {
  message_id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  context_payload: import("@pilot/ui").HelpContextPayload | null;
  retrieved_chunks: { count: number; article_ids: string[] } | null;
  voice_used: boolean;
}

export interface HelpSessionDetailResponse {
  session_id: string;
  title: string | null;
  outcome: string | null;
  messages: HelpMessageDetail[];
}

export interface HelpSessionFeedbackRequest {
  signal: "resolved" | "escalated" | "abandoned";
}

export interface HelpSessionFeedbackResponse {
  session_id: string;
  outcome: string;
}

export interface HelpSessionDeleteResponse {
  message: "Session deleted";
  session_id: string;
}

export interface HelpArticleResponse {
  article_id: string;
  title: string;
  category: string;
  content_markdown: string;
  audience: string[];
  last_updated: string;
}

// ── Feedback types ────────────────────────────────────────────────────────

export type FeedbackCategory =
  | "bug"
  | "feature_request"
  | "question"
  | "general";

export interface FeedbackSubmission {
  category: FeedbackCategory;
  body: string;
  from_help_chat_session_id?: string;
}

export interface FeedbackSubmitResponse {
  submission_id: string;
  category: FeedbackCategory;
  submitted_at: string;
  confirmation_message: string;
}

// ── Panel state types ─────────────────────────────────────────────────────

export type HelpPanelView = "chat" | "history";

export interface HelpPanelState {
  isOpen: boolean;
  view: HelpPanelView;
  context: import("@pilot/ui").HelpContextPayload | null;
  activeSessionId: string | null;
  // Actions
  open: () => void;
  close: () => void;
  toggle: () => void;
  openWithContext: (payload: import("@pilot/ui").HelpContextPayload) => void;
  clearContext: () => void;
  setActiveSession: (id: string | null) => void;
  setView: (view: HelpPanelView) => void;
}

// ── Session list item ─────────────────────────────────────────────────────

export interface HelpSessionListItem {
  session_id: string;
  title: string | null;
  started_at: string;
  last_activity_at: string;
  message_count: number;
  outcome: "resolved" | "escalated" | "abandoned" | null;
}
