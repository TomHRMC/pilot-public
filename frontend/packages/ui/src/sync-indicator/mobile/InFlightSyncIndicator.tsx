/**
 * InFlightSyncIndicator — Mobile (unified FE-B15)
 *
 * Location: packages/ui/src/sync-indicator/mobile/InFlightSyncIndicator.tsx
 *
 * FE-B1: Skeleton. Dot had no color — transparent/invisible (critical bug).
 * FE-B15 changes:
 *   - Fix dot backgroundColor: now derived from state × pendingCount × amberThreshold
 *   - Apply amberThreshold instead of discarding it (was `void _amberThreshold`)
 *   - Wire onResolve: wrap outer View in Pressable, call onResolve() on press
 *   - Add tap detail bottom sheet with pendingItems (up to 5)
 *   - Finalize state label copy (matches web spec)
 *   - Respect manualTriggerSupported
 *
 * Token mapping (H section of batch-fe-b15-design.md):
 *   idle (0 pending)               → tokens.colors.margin[400]
 *   synced-pending (≤ threshold)   → tokens.colors.margin[400]
 *   synced-pending (> threshold)   → tokens.colors.alert[400]
 *   syncing                        → tokens.colors.alert[400] (with Animated.loop)
 *   error                          → tokens.colors.fault[600]
 *   paused                         → tokens.colors.neutral[400]
 */

import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  Pressable,
  Modal,
  ScrollView,
  TouchableOpacity,
  Animated,
} from "react-native";
import {
  colors,
  mobileFontSizes,
  mobileLineHeights,
  fontWeights,
  spacing,
  radii,
} from "../../tokens";
import type {
  InFlightSyncIndicatorProps,
  SyncState,
  PendingItem,
} from "../types";

// ─── Dot color ────────────────────────────────────────────────────────────────

function getDotColor(
  state: SyncState,
  pendingCount: number,
  amberThreshold: number,
): string {
  switch (state) {
    case "idle":
      return colors.margin[400];
    case "syncing":
      return colors.alert[400];
    case "error":
      return colors.fault[600];
    case "paused":
      return colors.neutral[400];
    case "synced-pending":
      return pendingCount >= amberThreshold
        ? colors.alert[400]
        : colors.margin[400];
    default:
      return colors.neutral[400];
  }
}

// ─── Badge background color ────────────────────────────────────────────────────

function getBadgeBgColor(state: SyncState): string {
  switch (state) {
    case "error":
      return colors.fault[100];
    case "paused":
      return colors.neutral[100];
    default:
      return colors.alert[100];
  }
}

function getBadgeTextColor(state: SyncState): string {
  switch (state) {
    case "error":
      return colors.fault[800];
    case "paused":
      return colors.neutral[600];
    default:
      return colors.alert[800];
  }
}

// ─── State label copy ─────────────────────────────────────────────────────────

function formatRelativeTime(date: Date): string {
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1_000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h ago`;
}

function formatTimeUntil(date: Date): string {
  const diffMs = date.getTime() - Date.now();
  if (diffMs <= 0) return "now";
  const diffSec = Math.floor(diffMs / 1_000);
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h`;
}

function getStateLabel(
  state: SyncState,
  pendingCount: number,
  lastSyncedAt?: Date,
  nextSyncAt?: Date,
): string {
  switch (state) {
    case "idle": {
      if (lastSyncedAt) {
        return `Synced · last ${formatRelativeTime(lastSyncedAt)}`;
      }
      return "In sync";
    }
    case "synced-pending": {
      const timeStr = nextSyncAt
        ? ` · syncing in ${formatTimeUntil(nextSyncAt)}`
        : "";
      return `Synced · ${pendingCount} pending${timeStr}`;
    }
    case "syncing":
      return pendingCount > 0
        ? `Syncing ${pendingCount} change${pendingCount === 1 ? "" : "s"}…`
        : "Syncing…";
    case "error":
      return pendingCount > 0
        ? `Sync error · ${pendingCount} pending`
        : "Sync error";
    case "paused":
      return pendingCount > 0
        ? `Paused · ${pendingCount} queued`
        : "Sync paused";
    default:
      return "Unknown";
  }
}

// ─── Pending items detail sheet ───────────────────────────────────────────────

interface PendingDetailSheetProps {
  visible: boolean;
  pendingItems: PendingItem[];
  pendingCount: number;
  stateLabel: string;
  onClose: () => void;
}

function PendingDetailSheet({
  visible,
  pendingItems,
  pendingCount,
  stateLabel,
  onClose,
}: PendingDetailSheetProps) {
  const shown = pendingItems.slice(0, 5);
  const overflow = pendingCount - shown.length;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
      accessibilityViewIsModal
    >
      <TouchableOpacity
        style={{
          flex: 1,
          backgroundColor: colors.neutral[900],
          opacity: 0.9,
          justifyContent: "flex-end",
        }}
        activeOpacity={1}
        onPress={onClose}
        accessible={false}
      >
        <View
          style={{
            backgroundColor: colors.neutral[50],
            borderTopLeftRadius: radii.xl,
            borderTopRightRadius: radii.xl,
            paddingTop: spacing[4],
            paddingBottom: spacing[8],
            paddingHorizontal: spacing[4],
            maxHeight: "60%",
          }}
          accessible
          accessibilityLabel={`Sync details: ${stateLabel}`}
        >
          {/* Handle */}
          <View
            style={{
              alignSelf: "center",
              width: 36,
              height: 4,
              borderRadius: radii.full,
              backgroundColor: colors.neutral[200],
              marginBottom: spacing[4],
            }}
          />

          <Text
            style={{
              fontSize: mobileFontSizes.body,
              fontWeight: String(fontWeights.medium) as "500",
              color: colors.neutral[900],
              marginBottom: spacing[3],
            }}
          >
            {stateLabel}
          </Text>

          <ScrollView>
            {shown.map((item, idx) => (
              <View
                key={idx}
                style={{
                  flexDirection: "row",
                  alignItems: "flex-start",
                  gap: spacing[2],
                  paddingVertical: spacing[2],
                  borderBottomWidth: idx < shown.length - 1 ? 1 : 0,
                  borderBottomColor: colors.neutral[200],
                }}
              >
                <View
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: radii.full,
                    backgroundColor: colors.neutral[400],
                    marginTop: 5,
                    flexShrink: 0,
                  }}
                />
                <Text
                  style={{
                    flex: 1,
                    fontSize: mobileFontSizes.caption,
                    color: colors.neutral[600],
                  }}
                >
                  {item.label}
                </Text>
              </View>
            ))}
            {overflow > 0 && (
              <Text
                style={{
                  fontSize: mobileFontSizes.caption,
                  color: colors.neutral[400],
                  fontStyle: "italic",
                  marginTop: spacing[2],
                }}
              >
                +{overflow} more
              </Text>
            )}
          </ScrollView>

          <Pressable
            onPress={onClose}
            style={{
              marginTop: spacing[4],
              paddingVertical: spacing[3],
              borderRadius: radii.md,
              backgroundColor: colors.neutral[100],
              alignItems: "center",
            }}
            accessibilityRole="button"
            accessibilityLabel="Close sync details"
          >
            <Text
              style={{
                fontSize: mobileFontSizes.body,
                color: colors.neutral[600],
                fontWeight: String(fontWeights.medium) as "500",
              }}
            >
              Close
            </Text>
          </Pressable>
        </View>
      </TouchableOpacity>
    </Modal>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * InFlightSyncIndicator (mobile — unified FE-B15)
 */
export function InFlightSyncIndicator({
  surface,
  pendingCount = 0,
  lastSyncedAt,
  state = "idle",
  amberThreshold = 5,
  onManualSync,
  manualTriggerSupported = true,
  compact = false,
  onResolve,
  pendingItems = [],
  nextSyncAt,
  testID,
}: InFlightSyncIndicatorProps) {
  const [detailSheetOpen, setDetailSheetOpen] = useState(false);

  const dotColor = getDotColor(state, pendingCount, amberThreshold);
  const stateLabel = getStateLabel(
    state,
    pendingCount,
    lastSyncedAt,
    nextSyncAt,
  );
  const showBadge = pendingCount > 0;

  const showManualSync =
    state === "synced-pending" &&
    !!onManualSync &&
    manualTriggerSupported !== false &&
    surface !== "mobile-sync" &&
    surface !== "background-sync";

  // Press handler: show detail sheet (if pendingItems present), otherwise call onResolve
  const handlePress = () => {
    if (pendingItems.length > 0 && !compact) {
      setDetailSheetOpen(true);
    } else if (onResolve) {
      onResolve();
    }
  };

  // Dot pulse animation for syncing state
  const pulseAnim = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (state === "syncing") {
      const loop = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 0.3,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ]),
      );
      loop.start();
      return () => loop.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [state, pulseAnim]);

  const isInteractive = !!onResolve || pendingItems.length > 0;

  // ── Compact mode ──────────────────────────────────────────────────────────

  if (compact) {
    return (
      <Pressable
        onPress={isInteractive ? handlePress : undefined}
        testID={testID ?? `sync-indicator-${surface}`}
        accessibilityLabel={`${surface} sync: ${stateLabel}${showBadge ? `, ${pendingCount} pending` : ""}`}
        accessibilityRole={isInteractive ? "button" : "text"}
        style={{ flexDirection: "row", alignItems: "center", gap: spacing[1] }}
      >
        <Animated.View
          style={{
            width: spacing[2],
            height: spacing[2],
            borderRadius: radii.full,
            backgroundColor: dotColor,
            opacity: state === "syncing" ? pulseAnim : 1,
          }}
        />
        {showBadge && (
          <View
            style={{
              minWidth: spacing[4],
              height: spacing[4],
              borderRadius: radii.full,
              backgroundColor: getBadgeBgColor(state),
              alignItems: "center",
              justifyContent: "center",
              paddingHorizontal: spacing[1],
            }}
            accessibilityLabel={`${pendingCount} pending`}
          >
            <Text
              style={{
                fontSize: mobileFontSizes.caption,
                fontWeight: String(fontWeights.medium) as "500",
                color: getBadgeTextColor(state),
              }}
            >
              {pendingCount}
            </Text>
          </View>
        )}
      </Pressable>
    );
  }

  // ── Full mode ─────────────────────────────────────────────────────────────

  return (
    <>
      <Pressable
        onPress={isInteractive ? handlePress : undefined}
        testID={testID ?? `sync-indicator-${surface}`}
        accessibilityLabel={`${surface} sync: ${stateLabel}${showBadge ? `, ${pendingCount} pending` : ""}${isInteractive ? ". Tap for details." : ""}`}
        accessibilityRole={isInteractive ? "button" : "text"}
        style={{ flexDirection: "row", alignItems: "center", gap: spacing[2] }}
      >
        {/* Status dot with pulse animation for syncing */}
        <Animated.View
          style={{
            width: spacing[2],
            height: spacing[2],
            borderRadius: radii.full,
            backgroundColor: dotColor,
            opacity: state === "syncing" ? pulseAnim : 1,
          }}
          accessibilityElementsHidden
        />

        {/* State label */}
        <Text
          style={{
            fontSize: mobileFontSizes.body,
            lineHeight: mobileLineHeights.body,
            color: colors.neutral[600],
          }}
        >
          {stateLabel}
        </Text>

        {/* Pending count badge */}
        {showBadge && (
          <View
            style={{
              minWidth: spacing[4],
              height: spacing[4],
              borderRadius: radii.full,
              backgroundColor: getBadgeBgColor(state),
              alignItems: "center",
              justifyContent: "center",
              paddingHorizontal: spacing[1],
            }}
            accessibilityLabel={`${pendingCount} pending`}
          >
            <Text
              style={{
                fontSize: mobileFontSizes.caption,
                fontWeight: String(fontWeights.medium) as "500",
                color: getBadgeTextColor(state),
              }}
            >
              {pendingCount}
            </Text>
          </View>
        )}

        {/* Manual sync link */}
        {showManualSync && (
          <Pressable
            onPress={onManualSync}
            accessibilityRole="button"
            accessibilityLabel="Sync now"
          >
            <Text
              style={{
                fontSize: mobileFontSizes.body,
                textDecorationLine: "underline",
                color: colors.brand[600],
              }}
            >
              Sync now
            </Text>
          </Pressable>
        )}
      </Pressable>

      {/* Tap detail bottom sheet */}
      {pendingItems.length > 0 && (
        <PendingDetailSheet
          visible={detailSheetOpen}
          pendingItems={pendingItems}
          pendingCount={pendingCount}
          stateLabel={stateLabel}
          onClose={() => {
            setDetailSheetOpen(false);
            // If onResolve is present, call it after closing detail
          }}
        />
      )}
    </>
  );
}
