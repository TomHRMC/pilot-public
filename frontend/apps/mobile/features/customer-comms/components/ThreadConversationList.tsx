/**
 * ThreadConversationList — Scrollable FlatList of SmsThreadBubble components
 *
 * Location: apps/mobile/features/customer-comms/components/ThreadConversationList.tsx
 *
 * Inverted list (newest at bottom). Loads paginated messages.
 * Uses SmsThreadBubble.native.tsx from packages/ui (platform-resolved).
 *
 * Design doc Section A.3.1, D.2
 */

import React, { useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { SmsThreadBubble } from "@pilot/ui";
import {
  colors,
  spacing,
  mobileFontSizes,
} from "../../../../../packages/ui/src/tokens";
import type { SmsMessage } from "@pilot/ui";

interface ThreadConversationListProps {
  messages: SmsMessage[];
  currentTechId: string;
  isLoading: boolean;
  isError: boolean;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
  testID?: string;
}

export function ThreadConversationList({
  messages,
  currentTechId,
  isLoading,
  isError,
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
  testID,
}: ThreadConversationListProps) {
  const renderItem = useCallback(
    ({ item }: { item: SmsMessage }) => (
      <SmsThreadBubble
        message={item}
        isOwnMessage={item.direction === "outbound"}
        showTimestamp
        showDeliveryStatus
        isPending={item.status === "pending_send"}
        testID={`bubble-${item.message_id}`}
      />
    ),
    [],
  );

  const keyExtractor = useCallback((item: SmsMessage) => item.message_id, []);

  const handleEndReached = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      onLoadMore();
    }
  }, [hasNextPage, isFetchingNextPage, onLoadMore]);

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
      data={messages}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      style={styles.list}
      contentContainerStyle={styles.contentContainer}
      onEndReached={handleEndReached}
      onEndReachedThreshold={0.3}
      ListEmptyComponent={
        <View style={styles.emptyState} testID="thread-empty-state">
          <Text style={styles.emptyText}>
            Conversation started. Your messages will appear here.
          </Text>
        </View>
      }
      ListFooterComponent={
        isFetchingNextPage ? (
          <ActivityIndicator
            color={colors.brand[600]}
            style={styles.loadMoreIndicator}
          />
        ) : null
      }
      testID={testID ?? "thread-conversation-list"}
    />
  );
}

const styles = StyleSheet.create({
  list: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  contentContainer: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
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
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 80,
    padding: spacing[4],
  },
  emptyText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    textAlign: "center",
  },
  loadMoreIndicator: {
    paddingVertical: spacing[3],
  },
});
