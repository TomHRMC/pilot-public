/**
 * DiffView — track-changes diff renderer (mobile / React Native)
 *
 * Location: packages/ui/src/diff-view/mobile/DiffView.native.tsx
 *
 * Mobile implementation using React Native View/Text + token constants.
 * Web implementation: packages/ui/src/diff-view/web/DiffView.tsx
 * Shared types: packages/ui/src/diff-view/types.ts
 */

import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, spacing } from "../../tokens";
import type { DiffViewProps, DiffLineItem } from "../types";
import { DiffField } from "./DiffField.native";

export function DiffView(props: DiffViewProps) {
  const initialShowChanges =
    props.variant === "quote-line" ? (props.defaultShowChanges ?? true) : true;
  const [showChanges, setShowChanges] = useState(initialShowChanges);

  if (props.variant === "quote-line") {
    const changedLines = props.lineItems.filter(
      (li) => li.lineChangeType !== "unchanged",
    );
    const changesCount = changedLines.length;

    if (changesCount === 0) {
      return <Text style={styles.emptyText}>No changes to display.</Text>;
    }

    return (
      <View
        testID={props.testID ?? "diff-view"}
        accessibilityLabel="Quote line item changes"
      >
        {props.showToggle && (
          <Pressable
            onPress={() => setShowChanges((v) => !v)}
            accessibilityRole="button"
            accessibilityLabel={
              showChanges ? "Hide changes" : `Show changes (${changesCount})`
            }
            style={styles.toggleButton}
          >
            <Text style={styles.toggleText}>
              {showChanges ? "Hide changes" : `Show changes (${changesCount})`}
            </Text>
          </Pressable>
        )}

        {(!props.showToggle || showChanges) && (
          <View accessibilityLabel="Changed line items">
            {props.lineItems.map((lineItem) => (
              <MobileDiffLineItem
                key={lineItem.lineItemId}
                lineItem={lineItem}
                onRevertField={props.onRevertField}
              />
            ))}
          </View>
        )}
      </View>
    );
  }

  if (props.variant === "calendar-event" || props.variant === "qb-entity") {
    const defaultSideLabels = {
      "calendar-event": { base: "Pilot", modified: "Google Calendar" },
      "qb-entity": { base: "Pilot", modified: "QuickBooks" },
    };
    const sideLabels = props.sideLabels ?? defaultSideLabels[props.variant];

    return (
      <View
        testID={props.testID ?? "diff-view"}
        accessibilityLabel={`Changes for ${props.entityLabel}`}
      >
        <View style={styles.entityHeader}>
          <Text style={styles.entityLabel}>{props.entityLabel}</Text>
          <Text style={styles.sideLabels}>
            {sideLabels.base} → {sideLabels.modified}
          </Text>
        </View>
        {props.fieldDiffs.map((field) => (
          <DiffField key={field.fieldName} field={field} />
        ))}
      </View>
    );
  }

  // variant === "entity"
  return (
    <View
      testID={props.testID ?? "diff-view"}
      accessibilityLabel={`Changes for ${props.entityLabel}`}
    >
      <Text style={styles.entityLabel}>{props.entityLabel}</Text>
      {props.fieldDiffs.map((field) => (
        <DiffField key={field.fieldName} field={field} />
      ))}
    </View>
  );
}

interface MobileDiffLineItemProps {
  lineItem: DiffLineItem;
  onRevertField?: (pendingEditId: string) => void;
}

function MobileDiffLineItem({
  lineItem,
  onRevertField,
}: MobileDiffLineItemProps) {
  if (lineItem.lineChangeType === "unchanged") return null;

  const containerStyle = {
    added: styles.lineAdded,
    removed: styles.lineRemoved,
    modified: styles.lineModified,
    unchanged: styles.lineUnchanged,
  }[lineItem.lineChangeType];

  const badgeStyle = {
    added: styles.lineBadgeAdded,
    removed: styles.lineBadgeRemoved,
    modified: styles.lineBadgeModified,
    unchanged: styles.lineBadgeUnchanged,
  }[lineItem.lineChangeType];

  const badgeTextStyle = {
    added: styles.lineBadgeTextAdded,
    removed: styles.lineBadgeTextRemoved,
    modified: styles.lineBadgeTextModified,
    unchanged: styles.lineBadgeTextUnchanged,
  }[lineItem.lineChangeType];

  const badgeLabel = {
    added: "Added",
    removed: "Removed",
    modified: "Modified",
    unchanged: "Unchanged",
  }[lineItem.lineChangeType];

  return (
    <View
      style={[styles.lineContainer, containerStyle]}
      accessibilityLabel={`Line item: ${lineItem.label}, ${badgeLabel}`}
    >
      <View style={styles.lineHeader}>
        <Text style={styles.lineLabel}>{lineItem.label}</Text>
        <View style={[styles.lineBadge, badgeStyle]}>
          <Text style={[styles.lineBadgeText, badgeTextStyle]}>
            {badgeLabel}
          </Text>
        </View>
      </View>
      {lineItem.fields.map((field) => (
        <DiffField
          key={field.fieldName}
          field={field}
          onRevert={onRevertField}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  emptyText: {
    fontSize: 13,
    color: colors.neutral[400],
    fontStyle: "italic",
    paddingVertical: spacing[2],
  },
  toggleButton: {
    marginBottom: spacing[3],
  },
  toggleText: {
    fontSize: 13,
    color: colors.brand[600],
    fontWeight: "500",
  },
  entityHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing[3],
  },
  entityLabel: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.neutral[900],
  },
  sideLabels: {
    fontSize: 11,
    color: colors.neutral[400],
  },
  lineContainer: {
    borderRadius: 8,
    padding: spacing[3],
    marginBottom: spacing[2],
    borderWidth: 1,
  },
  lineAdded: {
    backgroundColor: colors.margin[50],
    borderColor: colors.margin[400],
  },
  lineRemoved: {
    backgroundColor: colors.fault[50],
    borderColor: colors.fault[400],
  },
  lineModified: {
    backgroundColor: colors.alert[50],
    borderColor: colors.alert[400],
  },
  lineUnchanged: {
    backgroundColor: colors.neutral[50],
    borderColor: colors.neutral[200],
  },
  lineHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing[2],
  },
  lineLabel: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.neutral[900],
    flex: 1,
  },
  lineBadge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: 4,
  },
  lineBadgeAdded: { backgroundColor: colors.margin[100] },
  lineBadgeRemoved: { backgroundColor: colors.fault[100] },
  lineBadgeModified: { backgroundColor: colors.alert[100] },
  lineBadgeUnchanged: { backgroundColor: colors.neutral[100] },
  lineBadgeText: { fontSize: 11, fontWeight: "500" },
  lineBadgeTextAdded: { color: colors.margin[800] },
  lineBadgeTextRemoved: { color: colors.fault[800] },
  lineBadgeTextModified: { color: colors.alert[800] },
  lineBadgeTextUnchanged: { color: colors.neutral[600] },
});
