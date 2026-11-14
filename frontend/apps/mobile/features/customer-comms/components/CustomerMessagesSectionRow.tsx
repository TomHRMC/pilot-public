/**
 * CustomerMessagesSectionRow — Home-screen inbox section widget
 *
 * Location: apps/mobile/features/customer-comms/components/CustomerMessagesSectionRow.tsx
 *
 * Shows up to 5 recent threads with unread count badge, last message preview,
 * customer name, relative timestamp. Tap row → thread screen.
 * Tap "View all" → full inbox list.
 *
 * Design doc Section A.3.1, Decision 1
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import {
  colors,
  spacing,
  mobileFontSizes,
  fontWeights,
} from "../../../../../packages/ui/src/tokens";
import { useCustomerThreads } from "../hooks/useCustomerThreads";

type AnyHref = Parameters<ReturnType<typeof useRouter>["push"]>[0];
function toHref(p: string): AnyHref {
  return p as AnyHref;
}

function getRelativeTime(isoDate: string): string {
  const diffMins = Math.floor(
    (Date.now() - new Date(isoDate).getTime()) / 60_000,
  );
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m`;
  const h = Math.floor(diffMins / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

interface CustomerMessagesSectionRowProps {
  testID?: string;
}

export function CustomerMessagesSectionRow({
  testID,
}: CustomerMessagesSectionRowProps) {
  const router = useRouter();
  const { threads, totalUnread } = useCustomerThreads();

  const recentThreads = threads.slice(0, 5);

  if (recentThreads.length === 0) {
    return null; // No threads → no section shown
  }

  return (
    <View
      style={styles.container}
      testID={testID ?? "customer-messages-section"}
    >
      {/* Section header */}
      <View style={styles.sectionHeader}>
        <View style={styles.titleRow}>
          <Text style={styles.sectionTitle}>Customer Messages</Text>
          {totalUnread > 0 && (
            <View style={styles.totalUnreadBadge} testID="total-unread-badge">
              <Text style={styles.totalUnreadText}>
                {totalUnread > 99 ? "99+" : totalUnread}
              </Text>
            </View>
          )}
        </View>
        <Pressable
          onPress={() => router.push(toHref("/(tabs)/(home)/inbox"))}
          testID="view-all-inbox"
        >
          <Text style={styles.viewAllText}>View all</Text>
        </Pressable>
      </View>

      {/* Thread rows */}
      {recentThreads.map((thread) => (
        <Pressable
          key={thread.thread_id}
          style={({ pressed }) => [
            styles.threadRow,
            pressed && styles.threadRowPressed,
          ]}
          onPress={() =>
            router.push(toHref(`/(tabs)/(home)/inbox/${thread.thread_id}`))
          }
          testID={`thread-preview-${thread.thread_id}`}
        >
          <View style={styles.threadContent}>
            <View style={styles.threadHeader}>
              <Text style={styles.customerName} numberOfLines={1}>
                {thread.customer_name}
              </Text>
              <Text style={styles.timestamp}>
                {getRelativeTime(thread.last_message_at)}
              </Text>
            </View>
            <Text style={styles.previewText} numberOfLines={1}>
              {thread.last_message_direction === "outbound" ? "You: " : ""}
              {thread.last_message_preview}
            </Text>
          </View>
          {thread.unread_count > 0 && (
            <View
              style={styles.unreadDot}
              testID={`preview-unread-${thread.thread_id}`}
            />
          )}
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[50],
    marginVertical: spacing[3],
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.neutral[200],
  },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  sectionTitle: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[900],
  },
  totalUnreadBadge: {
    backgroundColor: colors.brand[600],
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 6,
    alignItems: "center",
    justifyContent: "center",
  },
  totalUnreadText: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[50],
    fontWeight: String(fontWeights.medium) as "500",
  },
  viewAllText: {
    fontSize: mobileFontSizes.body,
    color: colors.brand[600],
  },
  threadRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  threadRowPressed: {
    backgroundColor: colors.neutral[100],
  },
  threadContent: {
    flex: 1,
    marginRight: spacing[2],
  },
  threadHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 2,
  },
  customerName: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[900],
    flex: 1,
    marginRight: spacing[2],
  },
  timestamp: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
  },
  previewText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[600],
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.brand[600],
  },
});
