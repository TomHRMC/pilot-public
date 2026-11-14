/**
 * RecentCustomerMessagesWidget — Dashboard widget showing last 10 messages
 *
 * Location: apps/web/src/features/dashboard/components/RecentCustomerMessagesWidget.tsx
 *
 * Queries ['dashboard-widget-recent-messages', { limit: 10 }] staleTime: 30s.
 * Click-through: /customers/[id]/comms?thread=[threadId]
 * SSE: 'customer_message_received' invalidates via useRecentCustomerMessages.
 *
 * Token classes (ZERO TOLERANCE):
 *   Outbound direction: text-brand-600
 *   Inbound direction: text-neutral-500
 *
 * Design doc Section A.2.2, Decision 5b
 */

"use client";

import React from "react";
import Link from "next/link";
import { useHasPermission } from "@pilot/ui";
import { useRecentCustomerMessages } from "../hooks/useRecentCustomerMessages";

function formatRelativeTime(isoDate: string): string {
  const diffMs = Date.now() - new Date(isoDate).getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const h = Math.floor(diffMins / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

interface RecentCustomerMessagesWidgetProps {
  className?: string;
  testID?: string;
}

export function RecentCustomerMessagesWidget({
  className,
  testID,
}: RecentCustomerMessagesWidgetProps) {
  // PLP-FIX-9 (INV-BUG-10): hide-not-disable for roles without comms grants.
  // Roles without communications.view render nothing — never the error branch.
  const canViewComms = useHasPermission("communications.view");
  const { messages, isLoading, isError } = useRecentCustomerMessages({
    limit: 10,
  });

  if (!canViewComms) return null;

  return (
    <div
      className={`bg-white border border-neutral-200 rounded-lg overflow-hidden ${className ?? ""}`}
      data-testid={testID ?? "recent-messages-widget"}
    >
      {/* Widget header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
        <h3 className="text-body font-medium text-neutral-900">
          Recent Customer Messages
        </h3>
        <Link
          href="/customers"
          className="text-caption text-brand-600 hover:text-brand-800"
        >
          View all
        </Link>
      </div>

      {/* Widget body */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-600" />
        </div>
      )}

      {isError && (
        <div className="px-4 py-4 text-body text-fault-600 text-center">
          Failed to load messages.
        </div>
      )}

      {!isLoading && !isError && messages.length === 0 && (
        <div
          className="px-4 py-6 text-body text-neutral-500 text-center"
          data-testid="widget-empty"
        >
          No customer messages yet.
        </div>
      )}

      {!isLoading && !isError && messages.length > 0 && (
        <ul
          className="divide-y divide-neutral-200"
          data-testid="recent-messages-list"
        >
          {messages.map((msg) => (
            <li key={msg.thread_id}>
              <Link
                href={`/customers/${msg.customer_id}/comms?thread=${msg.thread_id}`}
                className="flex items-start gap-3 px-4 py-3 hover:bg-neutral-50 transition-colors"
                data-testid={`recent-msg-row-${msg.thread_id}`}
              >
                {/* Direction indicator */}
                <span
                  className={`text-caption font-medium mt-0.5 flex-shrink-0 ${
                    msg.direction === "outbound"
                      ? "text-brand-600" // outbound — brand indigo
                      : "text-neutral-500" // inbound — neutral
                  }`}
                  aria-label={
                    msg.direction === "outbound"
                      ? "Outbound message"
                      : "Inbound message"
                  }
                >
                  {msg.direction === "outbound" ? "→" : "←"}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-body font-medium text-neutral-900 truncate">
                      {msg.customer_name}
                    </span>
                    <span className="text-caption text-neutral-400 flex-shrink-0">
                      {formatRelativeTime(msg.last_message_at)}
                    </span>
                  </div>
                  <p className="text-body text-neutral-600 truncate">
                    {msg.direction === "outbound" && msg.tech_name
                      ? `${msg.tech_name}: `
                      : ""}
                    {msg.body_preview}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
