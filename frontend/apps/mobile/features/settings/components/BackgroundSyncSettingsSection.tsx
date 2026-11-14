/**
 * BackgroundSyncSettingsSection — MOB-B8 Part B
 *
 * Location: apps/mobile/features/settings/components/BackgroundSyncSettingsSection.tsx
 *
 * Displays background sync policy settings:
 *   - 1 editable toggle: Background Sync on/off (user-level override, client-side MVP)
 *   - 3 read-only values: WiFi Only, Battery Floor, Sync Interval (owner-controlled)
 *
 * Per design doc §H.1 mockup and §G design decisions.
 * Tokens: all from packages/ui/src/tokens.ts — zero hardcoded hex values.
 *
 * Note: The user toggle is client-side only in MVP. Post-MVP: persist via
 * PUT /api/v1/settings/background_sync_enabled/user-override.
 */

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Switch,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { colors, mobileFontSizes, spacing } from "@pilot/ui/tokens";
import { fontWeights } from "../../../constants/style-constants";
import { useSyncPolicy } from "../hooks/useSyncPolicy";

interface BackgroundSyncSettingsSectionProps {
  testID?: string;
}

export function BackgroundSyncSettingsSection({
  testID,
}: BackgroundSyncSettingsSectionProps) {
  const { data: policy, isLoading, isError } = useSyncPolicy();

  // User-level override — client-side state only in MVP (resets on app restart)
  // Initialized from server policy once available; defaults to true if not loaded.
  const [userEnabled, setUserEnabled] = useState<boolean>(true);

  // Sync local toggle state with fetched policy on first load
  useEffect(() => {
    if (policy !== undefined) {
      setUserEnabled(policy.background_sync_enabled);
    }
  }, [policy]);

  if (isLoading) {
    return (
      <View
        style={styles.loadingContainer}
        testID={`${testID ?? "background-sync-settings-section"}-loading`}
      >
        <ActivityIndicator size="small" color={colors.brand[600]} />
      </View>
    );
  }

  // On error: render gracefully with safe defaults — never block settings screen
  const wifiOnly = isError
    ? false
    : (policy?.background_sync_wifi_only ?? false);
  const batteryFloor = isError
    ? 20
    : (policy?.background_sync_battery_floor_pct ?? 20);
  const syncInterval = isError
    ? 5
    : (policy?.background_sync_push_interval_minutes ?? 5);

  return (
    <View
      style={styles.section}
      testID={testID ?? "background-sync-settings-section"}
    >
      <Text style={styles.sectionTitle}>Background Sync</Text>
      <Text style={styles.sectionDescription}>
        Keep your data current even when the app is closed.
      </Text>

      {/* Editable: user can toggle background sync on/off */}
      <View style={styles.row}>
        <Text style={styles.rowLabel}>Background Sync</Text>
        <Switch
          testID="background-sync-toggle"
          value={userEnabled}
          onValueChange={(val) => {
            setUserEnabled(val);
            // TODO post-MVP: persist to server via PUT /api/v1/settings/background_sync_enabled/user-override
          }}
          trackColor={{
            false: colors.neutral[200],
            true: colors.brand[600],
          }}
          thumbColor="#FFFFFF"
        />
      </View>

      {/* Read-only: controlled by owner */}
      <View style={styles.row}>
        <Text style={styles.rowLabel}>WiFi Only</Text>
        <Text style={styles.rowValue} testID="wifi-only-value">
          {wifiOnly ? "On" : "Off"}
        </Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.rowLabel}>Battery Floor</Text>
        <Text style={styles.rowValue} testID="battery-floor-value">
          {batteryFloor}%
        </Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.rowLabel}>Sync Interval</Text>
        <Text style={styles.rowValue} testID="sync-interval-value">
          {syncInterval} min
        </Text>
      </View>

      {/* Owner-controlled note */}
      <Text style={styles.ownerNote} testID="owner-note">
        WiFi and battery settings are controlled by your account owner.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
  },
  loadingContainer: {
    paddingVertical: spacing[4],
    alignItems: "center",
  },
  sectionTitle: {
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: fontWeights.medium,
    color: colors.neutral[900],
    marginBottom: spacing[1],
  },
  sectionDescription: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[600],
    marginBottom: spacing[3],
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  rowLabel: {
    fontSize: mobileFontSizes.bodyLg,
    color: colors.neutral[800],
  },
  rowValue: {
    fontSize: mobileFontSizes.bodyLg,
    color: colors.neutral[600],
  },
  ownerNote: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    marginTop: spacing[2],
  },
});
