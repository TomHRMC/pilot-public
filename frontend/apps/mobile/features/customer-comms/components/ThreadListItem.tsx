/**
 * ThreadListItem — Single thread row in the inbox list
 *
 * Location: apps/mobile/features/customer-comms/components/ThreadListItem.tsx
 *
 * Shows: customer avatar initials, customer name, last message preview (50 chars),
 * relative time, unread count badge, opted-out indicator.
 *
 * Token refs (ZERO TOLERANCE — no hardcoded hex):
 *   Unread badge: brand[600] bg, neutral[50] text
 *   Opted-out indicator: fault[800] text
 *   Preview text: neutral[600]
 *   Unread preview: neutral[900]
 *
 * Design doc Section A.3.1
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import {
  colors,
  spacing,
  mobileFontSizes,
  fontWeights,
  radii,
} from "../../../../../packages/ui/src/tokens";
import type { SmsThreadListItem } from "@pilot/ui";

function getRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d`;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0]?.toUpperCase() ?? "")
    .join("");
}

interface ThreadListItemProps {
  thread: SmsThreadListItem;
  onPress: (threadId: string) => void;
  testID?: string;
}

export function ThreadListItem({
  thread,
  onPress,
  testID,
}: ThreadListItemProps) {
  const hasUnread = thread.unread_count > 0;
  const isOptedOut = thread.customer_sms_opted_out;

  return (
    <Pressable
      style={({ pressed }) => [styles.container, pressed && styles.pressed]}
      onPress={() => onPress(thread.thread_id)}
      accessibilityRole="button"
      accessibilityLabel={`${thread.customer_name}, ${thread.last_message_preview}`}
      testID={testID ?? `thread-list-item-${thread.thread_id}`}
    >
      {/* Avatar */}
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>
          {getInitials(thread.customer_name)}
        </Text>
      </View>

      {/* Content */}
      <View style={styles.content}>
        <View style={styles.headerRow}>
          <Text
            style={[styles.customerName, hasUnread && styles.unreadName]}
            numberOfLines={1}
          >
            {thread.customer_name}
          </Text>
          <Text style={styles.timestamp}>
            {getRelativeTime(thread.last_message_at)}
          </Text>
        </View>

        <View style={styles.previewRow}>
          <Text
            style={[styles.preview, hasUnread && styles.unreadPreview]}
            numberOfLines={1}
          >
            {thread.last_message_direction === "outbound" ? "You: " : ""}
            {thread.last_message_preview}
          </Text>

          {isOptedOut && (
            <Text
              style={styles.optedOutLabel}
              testID={`opted-out-${thread.thread_id}`}
            >
              opted out
            </Text>
          )}

          {hasUnread && (
            <View
              style={styles.unreadBadge}
              testID={`unread-badge-${thread.thread_id}`}
            >
              <Text style={styles.unreadBadgeText}>
                {thread.unread_count > 99 ? "99+" : thread.unread_count}
              </Text>
            </View>
          )}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.neutral[50],
  },
  pressed: {
    backgroundColor: colors.neutral[100],
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.brand[600],
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing[3],
  },
  avatarText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
  },
  content: {
    flex: 1,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 2,
  },
  customerName: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[900],
    flex: 1,
    marginRight: spacing[2],
  },
  unreadName: {
    fontWeight: String(fontWeights.medium) as "500",
  },
  timestamp: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
  },
  previewRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  preview: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[600], // neutral-600 for preview text
    flex: 1,
    marginRight: spacing[2],
  },
  unreadPreview: {
    color: colors.neutral[900],
  },
  optedOutLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.fault[800],
    marginRight: spacing[2],
  },
  unreadBadge: {
    backgroundColor: colors.brand[600], // brand-600 for unread count
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 6,
    alignItems: "center",
    justifyContent: "center",
  },
  unreadBadgeText: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[50],
    fontWeight: String(fontWeights.medium) as "500",
  },
});
