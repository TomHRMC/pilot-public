"use client";

/**
 * VoiceSessionDetailPage — voice session message history
 *
 * Location: apps/web/src/features/voice/components/VoiceSessionDetailPage.tsx
 *
 * Shows message history in chronological order.
 * User messages right-aligned; AI messages left-aligned.
 * Scrolls to bottom on load.
 */

import { useEffect, useRef } from "react";
import Link from "next/link";
import { LoadingState, EmptyState, ErrorState } from "@pilot/ui/states";
import { useVoiceSessionMessages } from "../hooks/useVoiceSessionMessages";
import { VoiceMessageBubble } from "./VoiceMessageBubble";

interface Props {
  sessionId: string;
}

export function VoiceSessionDetailPage({ sessionId }: Props) {
  const { data, isLoading, isError } = useVoiceSessionMessages(sessionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages load
  useEffect(() => {
    if (data?.messages && data.messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [data?.messages]);

  return (
    <div className="flex flex-col h-full bg-neutral-50">
      <header className="flex items-center gap-4 px-6 py-4 bg-white border-b border-neutral-200 shrink-0">
        <Link
          href="/voice"
          className="text-caption text-brand-600 hover:underline"
          data-testid="back-to-sessions"
        >
          ← Sessions
        </Link>
        <h1 className="text-h2 text-neutral-900 truncate">
          Session {sessionId.slice(-8)}
        </h1>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4">
        {isLoading && <LoadingState type="inline" label="Loading messages…" />}
        {isError && (
          <ErrorState
            type="server"
            title="Failed to load messages"
            description="Unable to fetch session messages."
          />
        )}
        {!isLoading &&
          !isError &&
          (!data?.messages || data.messages.length === 0) && (
            <EmptyState
              type="no-data"
              title="No messages yet"
              description="This session has no messages."
            />
          )}
        {!isLoading &&
          !isError &&
          data?.messages &&
          data.messages.length > 0 && (
            <div
              className="space-y-3 max-w-2xl mx-auto"
              data-testid="message-list"
            >
              {data.messages.map((message) => (
                <VoiceMessageBubble
                  key={message.message_id}
                  message={message}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
      </main>
    </div>
  );
}
