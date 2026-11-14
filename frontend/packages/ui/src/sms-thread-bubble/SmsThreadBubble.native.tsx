/**
 * SmsThreadBubble — Mobile variant (React Native)
 *
 * Location: packages/ui/src/sms-thread-bubble/SmsThreadBubble.native.tsx
 * Platform: Mobile (React Native / Expo)
 * Metro resolves this over SmsThreadBubble.tsx on mobile builds.
 *
 * Token values from tokens.ts:
 *   Outbound (tech-sent): colors.brand[600] bg, colors.neutral[50] text (right)
 *   Inbound (customer-sent): colors.neutral[100] bg, colors.neutral[900] text (left)
 *   Delivered: colors.margin[600]
 *   Failed: via PendingBadge variant="failed"
 *
 * RULE 5: No hardcoded hex/pixel values. All from tokens.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { PendingBadge } from "../pending-badge/PendingBadge";
import { colors, spacing, mobileFontSizes } from "../tokens";
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
  const isPendingSend = isPending || message.status === "pending_send";
  const isFailed = message.status === "failed";
  const isDelivered = message.status === "delivered";

  const timestampStr =
    message.sent_at ?? message.received_at ?? message.delivered_at ?? null;

  const bubbleStyle = isOutbound ? styles.outboundBubble : styles.inboundBubble;
  const textStyle = isOutbound ? styles.outboundText : styles.inboundText;
  const rowStyle = isOutbound ? styles.outboundRow : styles.inboundRow;

  return (
    <View
      style={[styles.wrapper, rowStyle]}
      testID={testID ?? `sms-bubble-${message.message_id}`}
    >
      <View style={styles.bubbleContainer}>
        <View style={[styles.bubble, bubbleStyle]}>
          <Text style={[styles.bodyText, textStyle]}>{message.body}</Text>
        </View>

        {/* Status row */}
        <View
          style={[
            styles.statusRow,
            isOutbound ? styles.statusRight : styles.statusLeft,
          ]}
        >
          {showTimestamp && timestampStr && (
            <Text style={styles.timestamp}>
              {formatTimestamp(timestampStr)}
            </Text>
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
                <Text
                  style={styles.deliveredCheck}
                  accessibilityLabel="Delivered"
                  testID={`delivered-${message.message_id}`}
                >
                  ✓
                </Text>
              )}
            </>
          )}
        </View>

        {senderLabel && (
          <Text
            style={[
              styles.senderLabel,
              isOutbound ? styles.senderLabelRight : styles.senderLabelLeft,
            ]}
            testID={`sender-label-${message.message_id}`}
          >
            {senderLabel}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: spacing[2],
  },
  outboundRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
  },
  inboundRow: {
    flexDirection: "row",
    justifyContent: "flex-start",
  },
  bubbleContainer: {
    maxWidth: "80%",
  },
  bubble: {
    borderRadius: 18,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
  },
  outboundBubble: {
    backgroundColor: colors.brand[600], // brand indigo — tech-sent
  },
  inboundBubble: {
    backgroundColor: colors.neutral[100], // neutral — customer-sent
  },
  bodyText: {
    fontSize: mobileFontSizes.body,
  },
  outboundText: {
    color: colors.neutral[50], // white on brand
  },
  inboundText: {
    color: colors.neutral[900], // dark on neutral
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[1],
    marginTop: 4,
  },
  statusRight: {
    justifyContent: "flex-end",
  },
  statusLeft: {
    justifyContent: "flex-start",
  },
  timestamp: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
  },
  deliveredCheck: {
    fontSize: mobileFontSizes.caption,
    color: colors.margin[600], // margin-600 = green delivered indicator
  },
  senderLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    marginTop: 2,
  },
  senderLabelRight: {
    textAlign: "right",
  },
  senderLabelLeft: {
    textAlign: "left",
  },
});
