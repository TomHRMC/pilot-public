/**
 * CustomerCommsHistoryView — Merged communication history list
 *
 * Location: apps/web/src/features/customer-comms/components/CustomerCommsHistoryView.tsx
 *
 * Combines two data sources so SD-02 seeded SMS thread messages are visible
 * from the customer comms tab when navigating from the inbox:
 *
 *   1. GET /api/v1/customers/{customerId}/communications
 *      → CommunicationHistoryItem[] (outbound template-based sends)
 *
 *   2. GET /api/v1/customers/{customerId}/threads  [MSW-bridged until backend ships]
 *      → SmsThread[] (inbound + outbound SMS thread messages from SD-02)
 *
 * Both sources are normalised to a flat `DisplayItem` and sorted newest-first.
 *
 * Design doc Section A.2.1, Decision 5a
 */

"use client";

import React from "react";
import { useCustomerCommsHistory } from "../hooks/useCustomerCommsHistory";
import { useCustomerCommsSse } from "../hooks/useCustomerCommsSse";
import { useCustomerSmsThreads } from "../hooks/useCustomerSmsThreads";

interface CustomerCommsHistoryViewProps {
  customerId: string;
  testID?: string;
}

/** Normalised row for unified display */
interface DisplayItem {
  key: string;
  channel: string;
  direction: "outbound" | "inbound";
  body: string;
  status: string;
  timestamp: string | null;
  source: "history" | "thread";
}

export function CustomerCommsHistoryView({
  customerId,
  testID,
}: CustomerCommsHistoryViewProps) {
  const {
    items: historyItems,
    isLoading: historyLoading,
    isError: historyError,
  } = useCustomerCommsHistory(customerId);

  const {
    threads,
    isLoading: threadsLoading,
    isError: threadsError,
  } = useCustomerSmsThreads(customerId);

  // SSE live updates — disabled until backend stream endpoint ships
  useCustomerCommsSse(customerId);

  const isLoading = historyLoading || threadsLoading;
  const isError = historyError || threadsError;

  // Normalise history items
  const fromHistory: DisplayItem[] = historyItems.map((item) => ({
    key: `hist-${item.communication_id}`,
    channel: item.actual_channel,
    direction: "outbound" as const,
    body: item.rendered_message,
    status: item.status,
    timestamp: item.sent_at,
    source: "history" as const,
  }));

  // Normalise thread messages
  const fromThreads: DisplayItem[] = threads.flatMap((thread) =>
    thread.messages.map((msg) => ({
      key: `thread-${msg.message_id}`,
      channel: msg.channel,
      direction: msg.direction,
      body: msg.body,
      status: msg.status,
      timestamp: msg.sent_at ?? msg.received_at,
      source: "thread" as const,
    })),
  );

  // Merge and sort newest-first, deduplicating by key
  const seenKeys = new Set<string>();
  const allItems = [...fromHistory, ...fromThreads]
    .filter((item) => {
      if (seenKeys.has(item.key)) return false;
      seenKeys.add(item.key);
      return true;
    })
    .sort((a, b) => {
      const aTime = a.timestamp ? new Date(a.timestamp).getTime() : 0;
      const bTime = b.timestamp ? new Date(b.timestamp).getTime() : 0;
      return bTime - aTime;
    });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="text-body text-fault-600 py-8"
        data-testid="comms-history-error"
      >
        Failed to load communication history. Try refreshing the page.
      </div>
    );
  }

  if (allItems.length === 0) {
    return (
      <p
        className="text-body text-neutral-500 py-8"
        data-testid="comms-history-empty"
      >
        No messages sent yet. Visit a customer to send their first message.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid={testID ?? "customer-comms-history"}>
      {allItems.map((item) => {
        const isSms = item.channel === "sms";
        const sentAt = item.timestamp
          ? new Date(item.timestamp).toLocaleString()
          : "—";
        const isInbound = item.direction === "inbound";
        return (
          <div
            key={item.key}
            className={[
              "rounded-lg border border-neutral-200 bg-white p-4",
              isInbound ? "border-l-4 border-l-brand-400" : "",
            ].join(" ")}
            data-testid={`comm-item-${item.key}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium ${
                    isSms
                      ? "bg-brand-50 text-brand-800"
                      : "bg-neutral-100 text-neutral-600"
                  }`}
                >
                  {isSms ? "SMS" : "Email"}
                </span>
                <span className="text-caption text-neutral-400 capitalize">
                  {item.direction}
                </span>
              </div>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium ${
                  item.status === "sent" || item.status === "delivered"
                    ? "bg-margin-50 text-margin-800"
                    : item.status === "failed"
                      ? "bg-fault-50 text-fault-800"
                      : item.status === "received"
                        ? "bg-brand-50 text-brand-700"
                        : "bg-alert-50 text-alert-800"
                }`}
              >
                {item.status}
              </span>
            </div>
            <p className="text-body text-neutral-900">{item.body}</p>
            <p className="text-caption text-neutral-400 mt-1">{sentAt}</p>
          </div>
        );
      })}
    </div>
  );
}
