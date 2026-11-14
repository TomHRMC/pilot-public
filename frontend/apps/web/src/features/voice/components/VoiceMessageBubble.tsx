"use client";

/**
 * VoiceMessageBubble — single voice message row
 *
 * Location: apps/web/src/features/voice/components/VoiceMessageBubble.tsx
 *
 * User messages: right-aligned, brand background
 * Assistant messages: left-aligned, neutral background
 */

import type { VoiceMessage } from "../hooks/useVoiceSessionMessages";

interface Props {
  message: VoiceMessage;
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function VoiceMessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      data-testid={`message-bubble-${message.message_id}`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 ${
          isUser
            ? "rounded-br-sm bg-brand-600 text-white"
            : "rounded-bl-sm bg-neutral-100 text-neutral-900"
        }`}
      >
        <p className="text-body-sm">{message.content_text}</p>

        {/* Structured content JSON card */}
        {message.structured_content_json && (
          <div className="mt-2 rounded-md border border-white/20 bg-white/10 p-2 text-caption">
            <p className="font-medium opacity-80">Structured data:</p>
            <pre className="mt-1 whitespace-pre-wrap text-caption opacity-70">
              {JSON.stringify(message.structured_content_json, null, 2)}
            </pre>
          </div>
        )}

        <p
          className={`mt-1 text-caption ${
            isUser ? "text-white/60" : "text-neutral-400"
          }`}
        >
          {formatTime(message.created_at)}
        </p>
      </div>
    </div>
  );
}
