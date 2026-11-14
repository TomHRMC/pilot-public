/**
 * Mobile Customer Communication History — (tabs)/customers/[id]/comms
 *
 * Per-customer outbound comm history on mobile.
 * FE-B10 extends with inbound threading.
 */

import React, { useState } from "react";
import {
  View,
  Text,
  Pressable,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { ErrorState } from "@pilot/ui/states";
import { colors, radii, spacing, fontWeights } from "@pilot/ui/tokens";
import type {
  CommunicationHistoryItem,
  CommunicationHistoryResponse,
} from "@pilot/ui";

// ── API ───────────────────────────────────────────────────────────────────────

async function fetchCustomerComms(
  customerId: string,
  page = 1,
): Promise<CommunicationHistoryResponse> {
  const res = await fetch(
    `/api/v1/customers/${customerId}/communications?page=${page}&page_size=20`,
  );
  if (!res.ok) throw new Error(`Failed to fetch comms: ${res.status}`);
  return res.json() as Promise<CommunicationHistoryResponse>;
}

// ── Row component ─────────────────────────────────────────────────────────────

function HistoryRow({ item }: { item: CommunicationHistoryItem }) {
  const sentAt = item.sent_at ? new Date(item.sent_at).toLocaleString() : "—";
  const isSms = item.actual_channel === "sms";

  return (
    <View style={styles.row} testID={`comms-row-${item.communication_id}`}>
      <View style={styles.rowLeft}>
        <View
          style={[
            styles.channelPill,
            isSms ? styles.smsPill : styles.emailPill,
          ]}
        >
          <Text
            style={[
              styles.channelPillText,
              isSms ? styles.smsPillText : styles.emailPillText,
            ]}
          >
            {isSms ? "💬 SMS" : "✉️ Email"}
          </Text>
        </View>
        {item.channel_override_flag && (
          <View style={styles.overrideBadge}>
            <Text style={styles.overrideBadgeText}>overridden</Text>
          </View>
        )}
      </View>
      <View style={styles.rowContent}>
        <Text style={styles.messageText} numberOfLines={2}>
          {item.rendered_message}
        </Text>
        <Text style={styles.metaText}>
          {item.template_code} · {sentAt}
        </Text>
      </View>
      <View
        style={[
          styles.statusBadge,
          item.status === "sent"
            ? styles.statusSent
            : item.status === "failed"
              ? styles.statusFailed
              : styles.statusPending,
        ]}
      >
        <Text
          style={[
            styles.statusText,
            item.status === "sent"
              ? styles.statusTextSent
              : item.status === "failed"
                ? styles.statusTextFailed
                : styles.statusTextPending,
          ]}
        >
          {item.status}
        </Text>
      </View>
    </View>
  );
}

// ── Screen component ──────────────────────────────────────────────────────────

export default function CustomerCommsScreen() {
  const { id: customerId } = useLocalSearchParams<{ id: string }>();
  const [page] = useState(1);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["customer-comms", customerId, page],
    queryFn: () => fetchCustomerComms(customerId, page),
    staleTime: 30_000,
  });

  return (
    <View style={styles.container} testID="customer-comms-mobile">
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          accessibilityLabel="Back"
        >
          <Text style={styles.backButtonText}>←</Text>
        </Pressable>
        <Text style={styles.headerTitle}>Communications</Text>
        <Pressable
          onPress={() =>
            router.push(`/(tabs)/customers/${customerId}/comms/send` as never)
          }
          style={styles.sendButton}
          accessibilityLabel="Send message"
          testID="send-message-btn"
        >
          <Text style={styles.sendButtonText}>Send</Text>
        </Pressable>
      </View>

      {isLoading && (
        <View style={styles.center}>
          <ActivityIndicator
            color={colors.brand[600]}
            accessibilityLabel="Loading"
          />
        </View>
      )}

      {isError && (
        <View style={styles.center}>
          <ErrorState
            type="server"
            title="Failed to load communications"
            description={
              error instanceof Error ? error.message : "Unknown error"
            }
            onRetry={() => refetch()}
          />
        </View>
      )}

      {data && (
        <FlatList<CommunicationHistoryItem>
          data={data.items}
          keyExtractor={(item) => item.communication_id}
          renderItem={({ item }) => <HistoryRow item={item} />}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
          ListEmptyComponent={
            <View style={styles.center}>
              <Text style={styles.emptyText}>No messages sent yet.</Text>
            </View>
          }
          testID="comms-history-list"
        />
      )}
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[4],
    backgroundColor: "#FFFFFF",
  },
  backButton: {
    minWidth: 44,
    minHeight: 44,
    justifyContent: "center",
    marginRight: spacing[3],
  },
  backButtonText: {
    color: colors.brand[600],
    fontSize: 20,
  },
  headerTitle: {
    flex: 1,
    color: colors.neutral[900],
    fontSize: 20,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 28,
  },
  sendButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    minHeight: 44,
    justifyContent: "center",
  },
  sendButtonText: {
    color: colors.neutral[50],
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
  },
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    backgroundColor: "#FFFFFF",
    gap: spacing[3],
  },
  rowLeft: {
    alignItems: "flex-start",
    gap: spacing[1],
    minWidth: 64,
  },
  channelPill: {
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  smsPill: { backgroundColor: colors.brand[50] },
  emailPill: { backgroundColor: colors.neutral[100] },
  channelPillText: {
    fontSize: 11,
    fontWeight: String(fontWeights.medium) as "500",
  },
  smsPillText: { color: colors.brand[800] },
  emailPillText: { color: colors.neutral[600] },
  overrideBadge: {
    backgroundColor: colors.alert[50],
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  overrideBadgeText: {
    color: colors.alert[800],
    fontSize: 11,
  },
  rowContent: {
    flex: 1,
  },
  messageText: {
    color: colors.neutral[900],
    fontSize: 13,
    lineHeight: 20,
  },
  metaText: {
    color: colors.neutral[400],
    fontSize: 11,
    lineHeight: 16,
    marginTop: 2,
  },
  statusBadge: {
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    alignSelf: "flex-start",
  },
  statusSent: { backgroundColor: colors.margin[50] },
  statusFailed: { backgroundColor: colors.fault[50] },
  statusPending: { backgroundColor: colors.alert[50] },
  statusText: {
    fontSize: 11,
    fontWeight: String(fontWeights.medium) as "500",
  },
  statusTextSent: { color: colors.margin[800] },
  statusTextFailed: { color: colors.fault[800] },
  statusTextPending: { color: colors.alert[800] },
  separator: {
    height: 1,
    backgroundColor: colors.neutral[100],
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing[6],
  },
  emptyText: {
    color: colors.neutral[400],
    fontSize: 15,
    lineHeight: 22,
  },
});
