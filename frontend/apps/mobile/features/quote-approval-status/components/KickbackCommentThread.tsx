/**
 * KickbackCommentThread — renders kickback comments from owner
 *
 * Location: apps/mobile/features/quote-approval-status/components/KickbackCommentThread.tsx
 *
 * Organizes overall and line-item comments from kickback annotations.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing, radii } from "@pilot/ui/tokens";
import type { QuoteComment } from "../hooks/useQuoteApprovalComments";

interface KickbackCommentThreadProps {
  comments: QuoteComment[];
  testID?: string;
}

export function KickbackCommentThread({
  comments,
  testID,
}: KickbackCommentThreadProps) {
  const overallComments = comments.filter(
    (c) => c.annotation_type === "overall",
  );
  const lineItemComments = comments.filter(
    (c) => c.annotation_type === "line_item",
  );
  const headerComments = comments.filter((c) => c.annotation_type === "header");

  if (comments.length === 0) {
    return <Text style={styles.empty}>No comments from the reviewer.</Text>;
  }

  return (
    <View testID={testID ?? "kickback-comment-thread"}>
      {/* Overall comments first */}
      {overallComments.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Overall feedback</Text>
          {overallComments.map((comment) => (
            <CommentBubble key={comment.id} comment={comment} />
          ))}
        </View>
      )}

      {/* Header comments */}
      {headerComments.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>General notes</Text>
          {headerComments.map((comment) => (
            <CommentBubble key={comment.id} comment={comment} />
          ))}
        </View>
      )}

      {/* Line item comments */}
      {lineItemComments.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Line item comments</Text>
          {lineItemComments.map((comment) => (
            <CommentBubble key={comment.id} comment={comment} showLineRef />
          ))}
        </View>
      )}
    </View>
  );
}

interface CommentBubbleProps {
  comment: QuoteComment;
  showLineRef?: boolean;
}

function CommentBubble({ comment, showLineRef = false }: CommentBubbleProps) {
  return (
    <View
      style={styles.bubble}
      accessibilityLabel={`Comment from ${comment.user_name}: ${comment.comment}`}
    >
      <View style={styles.bubbleHeader}>
        <Text style={styles.userName}>{comment.user_name}</Text>
        <Text style={styles.timestamp}>
          {new Date(comment.created_at).toLocaleDateString()}
        </Text>
      </View>
      {showLineRef && comment.affected_line_item_id && (
        <Text style={styles.lineRef}>
          Re: line item {comment.affected_line_item_id.slice(0, 8)}…
        </Text>
      )}
      <Text style={styles.commentText}>{comment.comment}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  empty: {
    fontSize: 13,
    color: colors.neutral[400],
    fontStyle: "italic",
    paddingVertical: spacing[2],
  },
  section: {
    marginBottom: spacing[4],
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: spacing[2],
  },
  bubble: {
    backgroundColor: colors.alert[50],
    borderRadius: radii.md,
    padding: spacing[3],
    marginBottom: spacing[2],
    borderLeftWidth: 3,
    borderLeftColor: colors.alert[400],
  },
  bubbleHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing[1],
  },
  userName: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.alert[800],
  },
  timestamp: {
    fontSize: 11,
    color: colors.neutral[400],
  },
  lineRef: {
    fontSize: 11,
    color: colors.neutral[400],
    fontStyle: "italic",
    marginBottom: spacing[1],
  },
  commentText: {
    fontSize: 13,
    color: colors.neutral[900],
    lineHeight: 20,
  },
});
