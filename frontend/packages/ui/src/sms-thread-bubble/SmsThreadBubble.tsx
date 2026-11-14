/**
 * SmsThreadBubble — Web variant (polymorphic)
 *
 * Location: packages/ui/src/sms-thread-bubble/SmsThreadBubble.tsx
 * Platform: Web (React DOM — Next.js)
 * Exported from: packages/ui/src/index.ts under // ── FE-B10 Exports ──
 *
 * Token classes (ZERO TOLERANCE):
 *   Outbound (tech-sent): bg-brand-600 text-white (right-aligned)
 *   Inbound (customer-sent): bg-neutral-100 text-neutral-900 (left-aligned)
 *   Delivered status: text-margin-600
 *   Failed status: text-fault-600 (via PendingBadge variant="failed")
 *   Pending badge: PendingBadge variant="pending" count=1
 *
 * RULE 5: Outbound messages continue to render correctly (FE-B6 unchanged).
 * Inbound messages added as new direction with distinct bubble style.
 */

import React from "react";
import { PendingBadge } from "../pending-badge/PendingBadge";
import type { SmsThreadBubbleProps } from "./types";

function formatTimestamp(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function SmsThreadBubble({
  message,
  showTimestamp = true,
  showDeliveryStatus = true,
  isPending = false,
  testID,
  senderLabel,
}: SmsThreadBubbleProps) {
  const isOutbound = message.direction === "outbound";

  const bubbleClass = isOutbound
    ? "bg-brand-600 text-white" // outbound: brand indigo, right-aligned
    : "bg-neutral-100 text-neutral-900"; // inbound: neutral, left-aligned

  const wrapperClass = isOutbound ? "flex justify-end" : "flex justify-start";

  const isPendingSend = isPending || message.status === "pending_send";
  const isFailed = message.status === "failed";
  const isDelivered = message.status === "delivered";

  const timestampStr =
    message.sent_at ?? message.received_at ?? message.delivered_at ?? null;

  return (
    <div
      className={`${wrapperClass} mb-2`}
      data-testid={testID ?? `sms-bubble-${message.message_id}`}
    >
      <div className="max-w-xs lg:max-w-md">
        <div className={`rounded-2xl px-4 py-3 ${bubbleClass}`}>
          <p className="text-body whitespace-pre-wrap break-words">
            {message.body}
          </p>
        </div>

        {/* Status row */}
        <div
          className={`flex items-center gap-1 mt-1 ${
            isOutbound ? "justify-end" : "justify-start"
          }`}
        >
          {showTimestamp && timestampStr && (
            <span className="text-caption text-neutral-400">
              {formatTimestamp(timestampStr)}
            </span>
          )}

          {showDeliveryStatus && isOutbound && (
            <>
              {isPendingSend && (
                <PendingBadge
                  count={1}
                  variant="pending"
                  testID={`pending-badge-${message.message_id}`}
                />
              )}
              {isFailed && (
                <PendingBadge
                  count={1}
                  variant="failed"
                  testID={`failed-badge-${message.message_id}`}
                />
              )}
              {isDelivered && !isPendingSend && (
                <span
                  className="text-caption text-margin-600"
                  aria-label="Delivered"
                  data-testid={`delivered-${message.message_id}`}
                >
                  ✓
                </span>
              )}
            </>
          )}
        </div>

        {senderLabel && (
          <p
            className={`text-xs text-neutral-400 mt-0.5 ${isOutbound ? "text-right" : "text-left"}`}
            data-testid={`sender-label-${message.message_id}`}
          >
            {senderLabel}
          </p>
        )}
      </div>
    </div>
  );
}
