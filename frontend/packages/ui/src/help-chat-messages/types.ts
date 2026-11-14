/**
 * HelpChatMessages shared types — FE-B16
 *
 * Location: packages/ui/src/help-chat-messages/types.ts
 *
 * Cross-platform types for the shared message list + composer zone.
 * Used by web HelpDrawer and mobile HelpChatScreen.
 * Interface is LOCKED after FE-B16.
 */

import type { HelpContextPayload } from "../help-anchor/types";

export type HelpFollowUpAction =
  | "read_full_article"
  | "walk_me_through_it"
  | "that_answered_it"
  | "still_confused";

export interface HelpChatMessage {
  message_id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string; // ISO timestamp
  context_payload: HelpContextPayload | null;
  retrieved_article_ids?: string[]; // Derived on assistant messages; empty = knowledge boundary
  voice_used: boolean;
  /** Derived client-side: true when retrieved_article_ids.length === 0 */
  is_knowledge_boundary?: boolean;
}

export interface HelpChatSession {
  session_id: string;
  title: string | null;
  started_at: string;
  last_activity_at: string;
  message_count: number;
  outcome: "resolved" | "escalated" | "abandoned" | null;
}

export interface HelpChatMessagesProps {
  /** The active help session (null while loading the first message) */
  session: HelpChatSession | null;
  /** Ordered array of messages to display */
  messages: HelpChatMessage[];
  /** Whether the AI is currently generating a response */
  isStreaming: boolean;
  /** Whether the initial session load is pending */
  isLoading: boolean;
  /** Error state if the last API call failed */
  error: Error | null;
  /** Called when the user submits a message (text or voice transcript) */
  onSendMessage: (text: string, voiceUsed?: boolean) => void;
  /** Called when the user taps a follow-up action button in an AI message */
  onFollowUpAction: (
    action: HelpFollowUpAction,
    message: HelpChatMessage,
  ) => void;
  /** Called when the user taps "Tell us →" on a knowledge boundary message */
  onEscalate: (session: HelpChatSession) => void;
  /** Called when the user taps 🔊 Listen on an AI message */
  onRequestTts: (text: string) => void;
  /** Platform-specific: padding bottom for keyboard avoidance (mobile only) */
  keyboardOffset?: number;
}
