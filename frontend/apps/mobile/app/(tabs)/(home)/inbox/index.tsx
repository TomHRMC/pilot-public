/**
 * CustomerThreadsInboxScreen — Full inbox list ("View all" destination)
 *
 * Location: apps/mobile/app/(tabs)/(home)/inbox/index.tsx
 * Route: /(tabs)/(home)/inbox
 *
 * Shows all tech's SMS threads grouped by unread first,
 * then by last message timestamp.
 *
 * Design doc Section A.3.1, Decision 1
 */

import React, { useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import {
  colors,
  spacing,
  mobileFontSizes,
} from "../../../../../../packages/ui/src/tokens";
import { useCustomerThreads } from "../../../../features/customer-comms/hooks/useCustomerThreads";
import { useMobileInboxSse } from "../../../../features/customer-comms/hooks/useMobileInboxSse";
import { ThreadListItem } from "../../../../features/customer-comms/components/ThreadListItem";
import type { SmsThreadListItem } from "@pilot/ui";

type AnyHref = Parameters<ReturnType<typeof useRouter>["push"]>[0];
function toHref(p: string): AnyHref {
  return p as AnyHref;
}

export default function CustomerThreadsInboxScreen() {
  const router = useRouter();
  const { threads, isLoading, isError, refetch } = useCustomerThreads();

  // SSE live updates for inbox
  useMobileInboxSse();

  const handleThreadPress = useCallback(
    (threadId: string) => {
      router.push(toHref(`/(tabs)/(home)/inbox/${threadId}`));
    },
    [router],
  );

  const renderItem = useCallback(
    ({ item }: { item: SmsThreadListItem }) => (
      <ThreadListItem
        thread={item}
        onPress={handleThreadPress}
        testID={`thread-row-${item.thread_id}`}
      />
    ),
    [handleThreadPress],
  );

  const keyExtractor = useCallback(
    (item: SmsThreadListItem) => item.thread_id,
    [],
  );

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.brand[600]} />
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>
          Failed to load messages. Pull to refresh.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={threads}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      style={styles.list}
      contentContainerStyle={
        threads.length === 0 ? styles.emptyContainer : undefined
      }
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={() => void refetch()}
          tintColor={colors.brand[600]}
        />
      }
      ListEmptyComponent={
        <View style={styles.emptyState} testID="inbox-empty-state">
          <Text style={styles.emptyTitle}>No customer messages yet</Text>
          <Text style={styles.emptyBody}>
            When customers reply, they&apos;ll appear here.
          </Text>
        </View>
      }
      ItemSeparatorComponent={() => <View style={styles.separator} />}
    />
  );
}

const styles = StyleSheet.create({
  list: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing[4],
  },
  errorText: {
    fontSize: mobileFontSizes.body,
    color: colors.fault[600],
    textAlign: "center",
  },
  emptyContainer: {
    flex: 1,
  },
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing[4],
    marginTop: 80,
  },
  emptyTitle: {
    fontSize: mobileFontSizes.h3,
    color: colors.neutral[900],
    marginBottom: spacing[2],
    textAlign: "center",
  },
  emptyBody: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    textAlign: "center",
  },
  separator: {
    height: 1,
    backgroundColor: colors.neutral[200],
    marginLeft: spacing[4] + 44 + spacing[3],
  },
});
