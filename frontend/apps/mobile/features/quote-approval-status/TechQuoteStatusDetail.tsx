/**
 * TechQuoteStatusDetail — tech-side quote detail with status and kickback comments
 *
 * Location: apps/mobile/features/quote-approval-status/TechQuoteStatusDetail.tsx
 *
 * Route: (home)/quotes/[id]
 * Shows kickback comments and owner-made changes after approval.
 */

import React, { useState } from "react";
import { View, Text, ScrollView, StyleSheet, Pressable } from "react-native";
import { DiffView } from "@pilot/ui";
import { colors, spacing, radii } from "@pilot/ui/tokens";
import { useQuoteApprovalComments } from "./hooks/useQuoteApprovalComments";
import { KickbackCommentThread } from "./components/KickbackCommentThread";
import { QuoteStatusPill } from "./components/QuoteStatusPill";
import type { TechQuoteStatus } from "./hooks/useTechQuotes";
import type { DiffField, DiffLineItem } from "@pilot/ui";

interface TechQuoteStatusDetailProps {
  quoteId: string;
  quoteNumber: string;
  status: TechQuoteStatus;
  customerName: string;
  hasOwnerEdits: boolean;
}

type Tab = "status" | "changes";

export function TechQuoteStatusDetail({
  quoteId,
  quoteNumber,
  status,
  customerName,
  hasOwnerEdits,
}: TechQuoteStatusDetailProps) {
  const [activeTab, setActiveTab] = useState<Tab>("status");
  const { data: comments, isLoading } = useQuoteApprovalComments(quoteId);

  const kickbackComments =
    comments?.filter((c) =>
      ["overall", "line_item", "header"].includes(c.annotation_type),
    ) ?? [];

  // Build owner-edit diff from line_item comments for the Changes tab
  const ownerEditDiffItems: DiffLineItem[] = (comments ?? [])
    .filter((c) => c.annotation_type === "line_item" && c.affected_line_item_id)
    .map((c) => {
      const field: DiffField = {
        fieldName: "owner_comment",
        label: "Owner comment",
        baseValue: null,
        modifiedValue: c.comment,
        changeType: "added" as const,
      };
      return {
        lineItemId: c.affected_line_item_id!,
        label: `Line item (${c.affected_line_item_id!.slice(0, 8)}…)`,
        customerVisible: true,
        lineChangeType: "modified" as const,
        fields: [field],
      };
    });

  const tabs: { id: Tab; label: string }[] = [
    { id: "status", label: "Status" },
    ...(hasOwnerEdits ? [{ id: "changes" as Tab, label: "Changes" }] : []),
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      accessibilityLabel={`Quote ${quoteNumber} detail`}
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.quoteNumber}>#{quoteNumber}</Text>
          <Text style={styles.customerName}>{customerName}</Text>
        </View>
        <QuoteStatusPill status={status} />
      </View>

      {/* Tab bar */}
      <View style={styles.tabBar} accessibilityRole="tablist">
        {tabs.map((tab) => (
          <Pressable
            key={tab.id}
            onPress={() => setActiveTab(tab.id)}
            style={[styles.tab, activeTab === tab.id && styles.tabActive]}
            accessibilityRole="tab"
            accessibilityState={{ selected: activeTab === tab.id }}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === tab.id && styles.tabTextActive,
              ]}
            >
              {tab.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Status tab */}
      {activeTab === "status" && (
        <View accessibilityLabel="Quote status">
          {status === "pending_approval" && (
            <View style={styles.infoBox}>
              <Text style={styles.infoTitle}>Awaiting review</Text>
              <Text style={styles.infoBody}>
                Your quote is waiting for owner review. You'll be notified when
                it's approved or if changes are needed.
              </Text>
            </View>
          )}

          {status === "approved" && kickbackComments.length === 0 && (
            <View style={[styles.infoBox, styles.infoBoxSuccess]}>
              <Text style={[styles.infoTitle, styles.infoTitleSuccess]}>
                Approved
              </Text>
              <Text style={styles.infoBody}>
                Your quote was approved. You can proceed with the job.
              </Text>
            </View>
          )}

          {status === "pending_approval" ||
          status === "draft" ||
          kickbackComments.length === 0 ? null : (
            <View>
              <Text style={styles.sectionHeading}>Reviewer feedback</Text>
              {isLoading ? (
                <Text style={styles.loadingText}>Loading comments…</Text>
              ) : (
                <KickbackCommentThread
                  comments={kickbackComments}
                  testID="kickback-comment-thread"
                />
              )}
            </View>
          )}

          {status === "rejected" && (
            <View style={[styles.infoBox, styles.infoBoxError]}>
              <Text style={[styles.infoTitle, styles.infoTitleError]}>
                Rejected
              </Text>
              <Text style={styles.infoBody}>
                This quote was rejected. See the comments above for details.
              </Text>
            </View>
          )}
        </View>
      )}

      {/* Changes tab */}
      {activeTab === "changes" && hasOwnerEdits && (
        <View accessibilityLabel="Owner changes">
          <Text style={styles.sectionHeading}>Changes made by owner</Text>
          {isLoading ? (
            <Text style={styles.loadingText}>Loading changes…</Text>
          ) : ownerEditDiffItems.length === 0 ? (
            <Text style={styles.emptyText}>
              No detailed change records available.
            </Text>
          ) : (
            <DiffView
              variant="quote-line"
              lineItems={ownerEditDiffItems}
              showToggle
              testID="tech-quote-changes-diff-view"
            />
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    padding: spacing[4],
    paddingBottom: spacing[8],
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: spacing[4],
  },
  quoteNumber: {
    fontSize: 20,
    fontWeight: "500",
    color: colors.neutral[900],
    marginBottom: spacing[1],
  },
  customerName: {
    fontSize: 13,
    color: colors.neutral[600],
  },
  tabBar: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    marginBottom: spacing[4],
  },
  tab: {
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[4],
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabActive: {
    borderBottomColor: colors.brand[600],
  },
  tabText: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.neutral[600],
  },
  tabTextActive: {
    color: colors.brand[600],
  },
  infoBox: {
    backgroundColor: colors.alert[50],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[4],
    borderLeftWidth: 3,
    borderLeftColor: colors.alert[400],
  },
  infoBoxSuccess: {
    backgroundColor: colors.margin[50],
    borderLeftColor: colors.margin[400],
  },
  infoBoxError: {
    backgroundColor: colors.fault[50],
    borderLeftColor: colors.fault[400],
  },
  infoTitle: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.alert[800],
    marginBottom: spacing[1],
  },
  infoTitleSuccess: {
    color: colors.margin[800],
  },
  infoTitleError: {
    color: colors.fault[800],
  },
  infoBody: {
    fontSize: 13,
    color: colors.neutral[600],
    lineHeight: 20,
  },
  sectionHeading: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.neutral[900],
    marginBottom: spacing[3],
  },
  loadingText: {
    fontSize: 13,
    color: colors.neutral[400],
    fontStyle: "italic",
  },
  emptyText: {
    fontSize: 13,
    color: colors.neutral[400],
    fontStyle: "italic",
  },
});
