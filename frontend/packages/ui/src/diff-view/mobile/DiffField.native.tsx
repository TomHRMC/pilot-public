/**
 * DiffField — single field diff row (mobile / React Native)
 *
 * Location: packages/ui/src/diff-view/mobile/DiffField.native.tsx
 * Internal component — not exported from barrel.
 *
 * Uses React Native StyleSheet + token constants.
 * NO hardcoded hex values.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, spacing } from "../../tokens";
import type { DiffField as DiffFieldType } from "../types";
import { deriveChangeType, fieldNameToLabel } from "../utils";

interface DiffFieldProps {
  field: DiffFieldType;
  onRevert?: (pendingEditId: string) => void;
}

export function DiffField({ field, onRevert }: DiffFieldProps) {
  const changeType =
    field.changeType ?? deriveChangeType(field.baseValue, field.modifiedValue);

  const label = field.label ?? fieldNameToLabel(field.fieldName);

  if (changeType === "unchanged") return null;

  const containerStyle = {
    modified: styles.containerModified,
    added: styles.containerAdded,
    removed: styles.containerRemoved,
  }[changeType];

  const labelStyle = {
    modified: styles.labelModified,
    added: styles.labelAdded,
    removed: styles.labelRemoved,
  }[changeType];

  const badgeStyle = {
    modified: styles.badgeModified,
    added: styles.badgeAdded,
    removed: styles.badgeRemoved,
  }[changeType];

  const badgeTextStyle = {
    modified: styles.badgeTextModified,
    added: styles.badgeTextAdded,
    removed: styles.badgeTextRemoved,
  }[changeType];

  const changeBadgeLabel = {
    modified: "Modified",
    added: "Added",
    removed: "Removed",
  }[changeType];

  const formatValue = (val: DiffFieldType["baseValue"]) => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "boolean") return val ? "Yes" : "No";
    return String(val);
  };

  return (
    <View
      style={[styles.container, containerStyle]}
      accessibilityLabel={`${label}: ${changeBadgeLabel}`}
    >
      <View style={styles.header}>
        <Text style={[styles.label, labelStyle]}>{label}</Text>
        <View style={[styles.badge, badgeStyle]}>
          <Text style={[styles.badgeText, badgeTextStyle]}>
            {changeBadgeLabel}
          </Text>
        </View>
      </View>

      {changeType === "modified" && (
        <View style={styles.valueRow}>
          <Text style={styles.oldValue}>{formatValue(field.baseValue)}</Text>
          <Text style={styles.arrow}>→</Text>
          <Text style={styles.newValue}>
            {formatValue(field.modifiedValue)}
          </Text>
        </View>
      )}

      {changeType === "added" && (
        <Text style={styles.addedValue}>
          {formatValue(field.modifiedValue)}
        </Text>
      )}

      {changeType === "removed" && (
        <Text style={styles.removedValue}>{formatValue(field.baseValue)}</Text>
      )}

      {field.annotation && (
        <Text style={styles.annotation}>{field.annotation}</Text>
      )}

      {onRevert && field.pendingEditId && (
        <Pressable
          onPress={() => onRevert(field.pendingEditId!)}
          accessibilityRole="button"
          accessibilityLabel={`Revert change to ${label}`}
          style={styles.revertButton}
        >
          <Text style={styles.revertText}>Revert this change</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderLeftWidth: 2,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: 4,
    marginBottom: spacing[1],
  },
  containerModified: {
    backgroundColor: colors.alert[50],
    borderLeftColor: colors.alert[400],
  },
  containerAdded: {
    backgroundColor: colors.margin[50],
    borderLeftColor: colors.margin[400],
  },
  containerRemoved: {
    backgroundColor: colors.fault[50],
    borderLeftColor: colors.fault[400],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing[1],
  },
  label: {
    fontSize: 11,
    fontWeight: "500",
  },
  labelModified: { color: colors.alert[800] },
  labelAdded: { color: colors.margin[800] },
  labelRemoved: { color: colors.fault[800] },
  badge: {
    paddingHorizontal: spacing[1],
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeModified: { backgroundColor: colors.alert[100] },
  badgeAdded: { backgroundColor: colors.margin[100] },
  badgeRemoved: { backgroundColor: colors.fault[100] },
  badgeText: { fontSize: 11, fontWeight: "500" },
  badgeTextModified: { color: colors.alert[800] },
  badgeTextAdded: { color: colors.margin[800] },
  badgeTextRemoved: { color: colors.fault[800] },
  valueRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  oldValue: {
    fontSize: 13,
    color: colors.neutral[400],
    textDecorationLine: "line-through",
  },
  arrow: {
    fontSize: 13,
    color: colors.neutral[400],
  },
  newValue: {
    fontSize: 13,
    color: colors.neutral[900],
    fontWeight: "500",
  },
  addedValue: {
    fontSize: 13,
    color: colors.margin[800],
    fontWeight: "500",
  },
  removedValue: {
    fontSize: 13,
    color: colors.fault[800],
    textDecorationLine: "line-through",
  },
  annotation: {
    fontSize: 11,
    color: colors.neutral[600],
    fontStyle: "italic",
    marginTop: spacing[1],
  },
  revertButton: {
    marginTop: spacing[1],
  },
  revertText: {
    fontSize: 11,
    color: colors.brand[600],
    textDecorationLine: "underline",
  },
});
