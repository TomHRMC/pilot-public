/**
 * HelpChatMessages — web implementation — FE-B16
 *
 * Location: packages/ui/src/help-chat-messages/web/HelpChatMessages.tsx
 *
 * Shared message list + composer zone used inside the web HelpDrawer.
 * RULE 2: No MessagePreviewModal or usePreviewBeforeSend imports.
 * RULE 3: No embedding/RAG/pgvector code.
 */

import React, { useEffect, useRef, useState } from "react";
import type {
  HelpChatMessagesProps,
  HelpChatMessage,
  HelpFollowUpAction,
} from "../types";
import { KnowledgeBoundaryMessage } from "../../knowledge-boundary-message/web/KnowledgeBoundaryMessage";

// ── Typing indicator ────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div
      data-testid="help-typing-indicator"
      className="flex items-center gap-1 px-3 py-2 bg-neutral-50 border border-neutral-200 rounded-lg max-w-[80px]"
    >
      <span className="w-2 h-2 bg-neutral-300 animate-pulse rounded-full [animation-delay:0ms]" />
      <span className="w-2 h-2 bg-neutral-300 animate-pulse rounded-full [animation-delay:200ms]" />
      <span className="w-2 h-2 bg-neutral-300 animate-pulse rounded-full [animation-delay:400ms]" />
    </div>
  );
}

// ── Message bubble ──────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: HelpChatMessage;
  onFollowUpAction: (
    action: HelpFollowUpAction,
    message: HelpChatMessage,
  ) => void;
  onEscalate: () => void;
  onRequestTts: (text: string) => void;
}

function MessageBubble({
  message,
  onFollowUpAction,
  onEscalate,
  onRequestTts,
}: MessageBubbleProps) {
  const time = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (message.role === "user") {
    return (
      <div className="flex justify-end my-1" data-testid="help-message-user">
        <div className="bg-brand-50 border border-brand-100 rounded-lg px-3 py-2 max-w-[80%]">
          <p className="text-sm text-brand-900 whitespace-pre-wrap">
            {message.content}
          </p>
          <p className="text-xs text-brand-400 mt-1 text-right">{time}</p>
        </div>
      </div>
    );
  }

  // Assistant message — check for knowledge boundary
  if (message.is_knowledge_boundary) {
    return (
      <div className="flex justify-start my-1">
        <KnowledgeBoundaryMessage
          content={message.content}
          timestamp={new Date(message.created_at)}
          onEscalate={onEscalate}
        />
      </div>
    );
  }

  // Normal assistant message
  return (
    <div
      className="flex justify-start my-1"
      data-testid="help-message-assistant"
    >
      <div className="bg-neutral-50 border border-neutral-200 rounded-lg px-3 py-2 max-w-[85%]">
        {/* Header */}
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-xs font-medium text-neutral-500">Pilot AI</span>
          <span className="text-xs text-neutral-300">·</span>
          <span className="text-xs text-neutral-400">{time}</span>
          {/* TTS button */}
          <button
            type="button"
            aria-label="Listen to this response"
            onClick={() => onRequestTts(message.content)}
            className="ml-auto text-neutral-400 hover:text-brand-600 transition-colors text-xs"
          >
            🔊
          </button>
        </div>

        <p className="text-sm text-neutral-900 whitespace-pre-wrap leading-relaxed">
          {message.content}
        </p>

        {/* Follow-up action buttons */}
        <div className="flex flex-wrap gap-1.5 mt-2">
          <button
            type="button"
            onClick={() => onFollowUpAction("read_full_article", message)}
            className="bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-md text-xs px-2 py-1 transition-colors"
          >
            Read full article
          </button>
          <button
            type="button"
            onClick={() => onFollowUpAction("walk_me_through_it", message)}
            className="bg-brand-50 hover:bg-brand-100 text-brand-700 rounded-md text-xs px-2 py-1 transition-colors"
          >
            Walk me through it
          </button>
          <button
            type="button"
            onClick={() => onFollowUpAction("that_answered_it", message)}
            className="bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-md text-xs px-2 py-1 transition-colors"
          >
            ✓ That answered it
          </button>
          <button
            type="button"
            onClick={() => onFollowUpAction("still_confused", message)}
            className="bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-md text-xs px-2 py-1 transition-colors"
          >
            Still confused
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Composer zone ───────────────────────────────────────────────────────────

interface ComposerProps {
  onSendMessage: (text: string, voiceUsed?: boolean) => void;
  isStreaming: boolean;
  /** Called when mic button is activated — wires to useVoiceStream in HelpChatComposer */
  onMicPress?: () => void;
  voiceTranscript?: string;
  isRecording?: boolean;
}

function Composer({
  onSendMessage,
  isStreaming,
  onMicPress,
  voiceTranscript = "",
  isRecording = false,
}: ComposerProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // When voice transcript arrives, populate the input
  useEffect(() => {
    if (voiceTranscript) {
      setText(voiceTranscript);
      inputRef.current?.focus();
    }
  }, [voiceTranscript]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSendMessage(trimmed, false);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const trimmed = text.trim();
      if (trimmed && !isStreaming) {
        onSendMessage(trimmed, false);
        setText("");
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white border-t border-neutral-200 px-3 py-2"
      data-testid="help-composer"
    >
      <div className="flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          rows={1}
          disabled={isStreaming}
          data-testid="help-composer-input"
          className="flex-1 resize-none max-h-32 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-300 disabled:opacity-50"
        />

        {/* Mic button — voice dictation (RULE 1: composing useVoiceStream, not new infra) */}
        {onMicPress && (
          <button
            type="button"
            aria-label={isRecording ? "Stop recording" : "Start voice input"}
            onClick={onMicPress}
            data-testid="help-mic-button"
            className={[
              "flex-shrink-0 p-2 rounded-full transition-colors",
              isRecording
                ? "text-alert-500 animate-pulse"
                : "text-neutral-400 hover:text-brand-600",
            ].join(" ")}
          >
            🎤
          </button>
        )}

        {/* Send button */}
        <button
          type="submit"
          aria-label="Send message"
          disabled={!text.trim() || isStreaming}
          data-testid="help-send-button"
          className="flex-shrink-0 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </div>
    </form>
  );
}

// ── Empty state ─────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center flex-1 text-center px-4"
      data-testid="help-empty-state"
    >
      <div className="text-3xl mb-3">💬</div>
      <p className="text-neutral-700 font-medium text-sm">
        Hi! What can I help you with?
      </p>
      <p className="text-neutral-400 text-xs mt-1">
        Ask about features, settings, or anything in Pilot.
      </p>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function HelpChatMessages({
  session,
  messages,
  isStreaming,
  isLoading,
  error,
  onSendMessage,
  onFollowUpAction,
  onEscalate,
  onRequestTts,
}: HelpChatMessagesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleEscalate = () => {
    if (session) onEscalate(session);
  };

  return (
    <div className="flex flex-col h-full" data-testid="help-chat-messages">
      {/* Message list */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-1"
        data-testid="help-message-list"
      >
        {isLoading && (
          <div className="flex justify-center py-4">
            <span className="text-xs text-neutral-400">Loading…</span>
          </div>
        )}

        {!isLoading && messages.length === 0 && <EmptyState />}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.message_id}
            message={msg}
            onFollowUpAction={onFollowUpAction}
            onEscalate={handleEscalate}
            onRequestTts={onRequestTts}
          />
        ))}

        {isStreaming && (
          <div className="flex justify-start my-1">
            <TypingIndicator />
          </div>
        )}

        {error && (
          <div className="flex justify-center py-2">
            <p className="text-xs text-alert-600 bg-alert-50 border border-alert-200 rounded px-2 py-1">
              {error.message || "Something went wrong. Please try again."}
            </p>
          </div>
        )}
      </div>

      {/* Composer */}
      <Composer onSendMessage={onSendMessage} isStreaming={isStreaming} />

      {/* Anonymization transparency notice — LOCKED position per design doc I.3 */}
      <div
        className="bg-neutral-50 text-neutral-500 text-xs px-3 py-1.5 border-t border-neutral-100 text-center"
        data-testid="help-anonymization-notice"
      >
        Pilot uses help conversations to improve our help content. Personal info
        is removed before use.{" "}
        <button
          type="button"
          className="underline hover:text-neutral-700"
          onClick={() => onRequestTts("")}
        >
          Learn more
        </button>
      </div>
    </div>
  );
}
