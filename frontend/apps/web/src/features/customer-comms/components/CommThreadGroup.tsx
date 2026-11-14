/**
 * CommThreadGroup — Collapsible group for a single SMS thread
 *
 * Location: apps/web/src/features/customer-comms/components/CommThreadGroup.tsx
 *
 * Shows thread header (tech name, date range, unread count) and message list.
 * Collapsed by default; expands on header click.
 *
 * Token classes (ZERO TOLERANCE):
 *   Header bg: bg-neutral-50 border-b border-neutral-200
 *   Outbound bubble: bg-brand-600 text-white
 *   Inbound bubble: bg-neutral-100 text-neutral-900
 *
 * Design doc Section A.2.1, Decision 5a
 */

"use client";

import React, { useState } from "react";
import { SmsThreadBubble } from "@pilot/ui";
import type { SmsThread } from "@pilot/ui";

interface CommThreadGroupProps {
  thread: SmsThread;
  defaultExpanded?: boolean;
  testID?: string;
}

function formatDateRange(start: string, end: string): string {
  const s = new Date(start).toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
  const e = new Date(end).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return s === e ? s : `${s} – ${e}`;
}

export function CommThreadGroup({
  thread,
  defaultExpanded = false,
  testID,
}: CommThreadGroupProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div
      className="border border-neutral-200 rounded-lg overflow-hidden mb-4"
      data-testid={testID ?? `thread-group-${thread.thread_id}`}
    >
      {/* Thread header — collapsible trigger */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 border-b border-neutral-200 text-left hover:bg-neutral-100 transition-colors"
        onClick={() => setIsExpanded((v) => !v)}
        aria-expanded={isExpanded}
        data-testid={`thread-group-header-${thread.thread_id}`}
      >
        <div className="flex flex-col gap-0.5">
          {/* Task 3: customer name is primary identifier */}
          <span className="text-sm font-medium text-neutral-900">
            {thread.customer_name}
          </span>
          {/* Task 2: tech name + date as secondary, text-xs */}
          <span className="text-xs text-neutral-500">
            {thread.tech_name}
            {" · "}
            {formatDateRange(thread.first_message_at, thread.last_message_at)}
            {" · "}
            {thread.message_count} message
            {thread.message_count !== 1 ? "s" : ""}
          </span>
          {thread.originating_job_display && (
            <span className="text-xs text-neutral-600">
              {thread.originating_job_display}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {thread.unread_count > 0 && (
            <span
              className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-caption font-medium bg-brand-600 text-white"
              data-testid={`thread-unread-${thread.thread_id}`}
            >
              {thread.unread_count}
            </span>
          )}
          <span className="text-neutral-400 text-body">
            {isExpanded ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {/* Message list */}
      {isExpanded && (
        <div
          className="px-4 py-3 space-y-2 bg-neutral-50"
          data-testid={`thread-messages-${thread.thread_id}`}
        >
          {thread.messages.length === 0 ? (
            <p className="text-sm text-neutral-500 text-center py-4">
              No messages in this thread.
            </p>
          ) : (
            thread.messages.map((message) => (
              <SmsThreadBubble
                key={message.message_id}
                message={message}
                isOwnMessage={message.direction === "outbound"}
                showTimestamp
                showDeliveryStatus
                testID={`msg-bubble-${message.message_id}`}
                senderLabel={
                  message.direction === "outbound"
                    ? `From: ${thread.tech_name.split(" ")[0]}`
                    : `From: ${thread.customer_name}`
                }
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
