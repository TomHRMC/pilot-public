/**
 * ThreadHeader — Screen header for thread conversation
 *
 * Location: apps/mobile/features/customer-comms/components/ThreadHeader.tsx
 *
 * Shows: customer name, job context (if available), SmsOptOutBadge when opted out.
 *
 * Design doc Section A.3.1, Decision 7
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { SmsOptOutBadge } from "@pilot/ui";
import {
  colors,
  spacing,
  mobileFontSizes,
  fontWeights,
} from "../../../../../packages/ui/src/tokens";
import type { SmsThread } from "@pilot/ui";

interface ThreadHeaderProps {
  thread: SmsThread;
  testID?: string;
}

export function ThreadHeader({ thread, testID }: ThreadHeaderProps) {
  return (
    <View style={styles.container} testID={testID ?? "thread-header"}>
      <Text style={styles.customerName} testID="thread-customer-name">
        {thread.customer_name}
      </Text>

      {thread.originating_job_display && (
        <Text style={styles.jobContext} testID="thread-job-context">
          {thread.originating_job_display}
        </Text>
      )}

      {thread.customer_sms_opted_out && (
        <View style={styles.optOutBadgeWrapper}>
          <SmsOptOutBadge
            optedOutAt={thread.customer_opted_out_at}
            testID="thread-opt-out-badge"
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.neutral[50],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  customerName: {
    fontSize: mobileFontSizes.h3,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[900],
  },
  jobContext: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[600],
    marginTop: 2,
  },
  optOutBadgeWrapper: {
    marginTop: spacing[2],
  },
});
