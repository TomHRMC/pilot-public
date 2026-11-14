/**
 * UnroutedMessageQueue — Paginated list of unrouted inbound messages
 *
 * Location: apps/web/src/features/sms-unrouted/components/UnroutedMessageQueue.tsx
 *
 * Columns: received timestamp, sender phone (masked), message preview, Assign button.
 *
 * RULE 6: This surface is behind RoleGate(integrations.manage) — owner only.
 * The RoleGate is on the route page, not in this component.
 *
 * Design doc Section A.2.3, Decision 6
 */

"use client";

import React from "react";
import { UnroutedMessageRow } from "./UnroutedMessageRow";
import { useUnroutedMessages } from "../hooks/useUnroutedMessages";

interface UnroutedMessageQueueProps {
  testID?: string;
}

export function UnroutedMessageQueue({ testID }: UnroutedMessageQueueProps) {
  const { messages, totalCount, isLoading, isError } = useUnroutedMessages();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-body text-fault-600 text-center py-8">
        Failed to load unrouted messages. Try refreshing the page.
      </div>
    );
  }

  return (
    <div data-testid={testID ?? "unrouted-queue"}>
      {messages.length === 0 ? (
        <div
          className="text-body text-neutral-500 text-center py-12"
          data-testid="unrouted-empty"
        >
          No unrouted messages. All customer texts have been matched
          successfully.
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-body text-neutral-600">
              {totalCount} unrouted message{totalCount !== 1 ? "s" : ""}{" "}
              awaiting assignment
            </p>
          </div>

          <div className="border border-neutral-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-neutral-50 border-b border-neutral-200">
                <tr>
                  <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                    Received
                  </th>
                  <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                    From
                  </th>
                  <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                    Message
                  </th>
                  <th className="px-4 py-3 text-right text-caption font-medium text-neutral-600">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 bg-white">
                {messages.map((msg) => (
                  <UnroutedMessageRow
                    key={msg.unrouted_id}
                    message={msg}
                    testID={`row-${msg.unrouted_id}`}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
