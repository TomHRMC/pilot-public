/**
 * ConflictSummaryCard — Conflict summary card for voice session messages
 *
 * Location: apps/mobile/features/voice-quote-creation/components/ConflictSummaryCard.tsx
 *
 * Renders a simple conflict summary card with a "Resolve on web →" link.
 * Full conflict resolution is web-only per PRD (design decision §G).
 *
 * Per batch-mob-b6-design.md Step 7.
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Linking,
  Alert,
} from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ConflictSummaryPayload {
  conflict_id?: string;
  entity_type?: string; // 'customer' | 'quote' | 'invoice' | 'job'
  conflict_type?: string; // 'modified_modified' | 'deleted_modified' etc.
  summary?: string;
}

export interface ConflictSummaryCardProps {
  payload?: ConflictSummaryPayload;
  testID?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const WEB_BASE_URL = "https://app.pilotfortrades.com";

function getResolveUrl(
  entityType: string | undefined,
  conflictId: string | undefined,
): string {
  // Default to integrations/quickbooks/conflicts path for all types
  return `${WEB_BASE_URL}/settings/integrations/quickbooks/conflicts/${conflictId ?? ""}`;
}

function formatConflictType(conflictType: string | undefined): string {
  if (!conflictType) return "Unknown conflict";
  return conflictType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatEntityType(entityType: string | undefined): string {
  if (!entityType) return "Record";
  return entityType.charAt(0).toUpperCase() + entityType.slice(1);
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ConflictSummaryCard({
  payload,
  testID,
}: ConflictSummaryCardProps): React.ReactElement {
  const conflictId = payload?.conflict_id;
  const entityType = payload?.entity_type;
  const conflictType = payload?.conflict_type;
  const summary = payload?.summary;

  const handleResolvePress = async () => {
    const url = getResolveUrl(entityType, conflictId);
    const canOpen = await Linking.canOpenURL(url);
    if (canOpen) {
      await Linking.openURL(url);
    } else {
      Alert.alert(
        "Cannot open browser",
        "Please visit app.pilotfortrades.com to resolve this conflict.",
      );
    }
  };

  return (
    <View style={styles.card} testID={testID ?? "conflict-summary-card"}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.warningIcon}>
          <Text style={styles.warningIconText}>⚠</Text>
        </View>
        <Text style={styles.title} testID="conflict-title">
          {`Conflict: ${formatEntityType(entityType)} — ${formatConflictType(conflictType)}`}
        </Text>
      </View>

      {/* Summary text */}
      {summary ? (
        <Text style={styles.summary} testID="conflict-summary">
          {summary}
        </Text>
      ) : (
        <Text style={styles.summary} testID="conflict-summary">
          {`A sync conflict was detected on this ${entityType ?? "record"}. Resolve it on the web dashboard.`}
        </Text>
      )}

      {/* Conflict ID (for debugging) */}
      {conflictId ? (
        <Text style={styles.conflictId} testID="conflict-id">
          ID: {conflictId}
        </Text>
      ) : null}

      {/* Resolve on web button */}
      <Pressable
        style={styles.resolveButton}
        onPress={() => void handleResolvePress()}
        accessibilityRole="link"
        accessibilityLabel="Resolve conflict on web"
        testID="resolve-on-web-button"
      >
        <Text style={styles.resolveButtonText}>Resolve on web →</Text>
      </Pressable>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.neutral[50],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.alert[400],
    padding: spacing[4],
    marginVertical: spacing[2],
    gap: spacing[3],
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing[2],
  },
  warningIcon: {
    width: 20,
    height: 20,
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  warningIconText: {
    fontSize: 14,
    color: colors.alert[400],
    lineHeight: 18,
  },
  title: {
    fontSize: 13,
    color: colors.neutral[800],
    flex: 1,
    lineHeight: 18,
  },
  summary: {
    fontSize: 13,
    color: colors.neutral[600],
    lineHeight: 18,
  },
  conflictId: {
    fontSize: 11,
    color: colors.neutral[400],
    lineHeight: 14,
    fontFamily: "monospace",
  },
  resolveButton: {
    alignSelf: "flex-start",
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  resolveButtonText: {
    fontSize: 13,
    color: colors.neutral[50],
    lineHeight: 18,
  },
});
