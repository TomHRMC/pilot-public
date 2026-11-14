/**
 * ThreadConversationScreen — Full message history + composer
 *
 * Location: apps/mobile/app/(tabs)/(home)/inbox/[threadId].tsx
 * Route: /(tabs)/(home)/inbox/[threadId]
 *
 * Deep-link entry point from push notifications.
 * Cold-start: pilot:///(tabs)/(home)/inbox/[threadId]
 * Query param ?unread=true scrolls to first unread message.
 *
 * Fires mark-read on screen focus.
 * SSE live updates via useMobileInboxSse.
 *
 * Design doc Decision 1, Section A.3.1, D.2, D.7
 */

import React, { useEffect, useCallback } from "react";
import { View, StyleSheet } from "react-native";
import { useLocalSearchParams, useNavigation } from "expo-router";
import { colors } from "../../../../../../packages/ui/src/tokens";
import { useThreadMessages } from "../../../../features/customer-comms/hooks/useThreadMessages";
import { useMarkThreadRead } from "../../../../features/customer-comms/hooks/useMarkThreadRead";
import { useMobileInboxSse } from "../../../../features/customer-comms/hooks/useMobileInboxSse";
import { ThreadHeader } from "../../../../features/customer-comms/components/ThreadHeader";
import { ThreadConversationList } from "../../../../features/customer-comms/components/ThreadConversationList";
import { ReplyComposer } from "../../../../features/customer-comms/components/ReplyComposer";

export default function ThreadConversationScreen() {
  const { threadId } = useLocalSearchParams<{ threadId: string }>();
  const navigation = useNavigation();

  const {
    messages,
    thread,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
  } = useThreadMessages(threadId ?? "");

  const { mutate: markRead } = useMarkThreadRead();

  // SSE live updates — also invalidates this thread's messages cache
  useMobileInboxSse({ activeThreadId: threadId });

  // Mark as read when screen comes into focus
  useEffect(() => {
    if (threadId && thread?.unread_count && thread.unread_count > 0) {
      markRead(threadId);
    }
  }, [threadId, thread?.unread_count, markRead]);

  // Set navigation header title to customer name
  useEffect(() => {
    if (thread?.customer_name) {
      navigation.setOptions({ title: thread.customer_name });
    }
  }, [thread?.customer_name, navigation]);

  const handleLoadMore = useCallback(() => {
    void fetchNextPage();
  }, [fetchNextPage]);

  const isOptedOut = thread?.customer_sms_opted_out ?? false;
  const customerId = thread?.customer_id ?? "";

  return (
    <View style={styles.container}>
      {/* Thread header: customer name, job context, opt-out badge */}
      {thread && <ThreadHeader thread={thread} testID="thread-header" />}

      {/* Message list */}
      <ThreadConversationList
        messages={messages}
        currentTechId={thread?.tech_id ?? ""}
        isLoading={isLoading}
        isError={isError}
        hasNextPage={hasNextPage ?? false}
        isFetchingNextPage={isFetchingNextPage}
        onLoadMore={handleLoadMore}
        testID="conversation-list"
      />

      {/* Reply composer — only shown when thread is loaded */}
      {thread && customerId && (
        <ReplyComposer
          threadId={threadId ?? ""}
          customerId={customerId}
          isOptedOut={isOptedOut}
          testID="reply-composer"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
});
