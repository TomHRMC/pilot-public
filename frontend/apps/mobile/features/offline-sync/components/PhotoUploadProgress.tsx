/**
 * PhotoUploadProgress — Per-photo upload progress overlay
 *
 * Location: apps/mobile/features/offline-sync/components/PhotoUploadProgress.tsx
 *
 * Shown as an overlay on photo thumbnails. Four states:
 *   uploading  → progress bar + percentage
 *   wifi_pending → WiFi icon + "Waiting for WiFi"
 *   success   → checkmark (brief, then fades)
 *   failed    → error icon + "Tap to retry"
 *
 * Token colors (NO hardcoded hex):
 *   uploading  → colors.brand[400]
 *   wifi       → colors.alert[400]
 *   success    → colors.margin[400]
 *   failed     → colors.fault[400]
 *
 * Per batch-fe-b7-design.md Section A.3.4.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import type { LocalSyncStatus } from "../../../database/models/SyncableModel";

interface PhotoUploadProgressProps {
  uploadProgress: number; // 0–100
  localSyncStatus: LocalSyncStatus;
  wifiPending?: boolean;
  onRetry?: () => void;
  testID?: string;
}

export function PhotoUploadProgress({
  uploadProgress,
  localSyncStatus,
  wifiPending = false,
  onRetry,
  testID,
}: PhotoUploadProgressProps): React.ReactElement | null {
  // Don't render overlay when synced
  if (localSyncStatus === "synced") return null;

  if (wifiPending) {
    return (
      <View
        style={[styles.overlay, styles.overlayWifi]}
        testID={testID ?? "photo-wifi-pending"}
      >
        <Text style={styles.wifiIcon}>📶</Text>
        <Text style={[styles.label, { color: colors.alert[400] }]}>
          Waiting for WiFi
        </Text>
      </View>
    );
  }

  if (localSyncStatus === "failed") {
    return (
      <Pressable
        style={[styles.overlay, styles.overlayFailed]}
        onPress={onRetry}
        accessibilityRole="button"
        accessibilityLabel="Upload failed. Tap to retry"
        testID={testID ?? "photo-upload-failed"}
      >
        <Text style={styles.failedIcon}>⚠️</Text>
        <Text style={[styles.label, { color: colors.fault[400] }]}>
          Tap to retry
        </Text>
      </Pressable>
    );
  }

  if (localSyncStatus === "syncing" || localSyncStatus === "pending") {
    return (
      <View
        style={[styles.overlay, styles.overlayUploading]}
        testID={testID ?? "photo-upload-progress"}
        accessibilityLabel={`Uploading ${uploadProgress}%`}
      >
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${uploadProgress}%`,
                backgroundColor: colors.brand[400],
              },
            ]}
          />
        </View>
        <Text style={[styles.label, { color: colors.neutral[50] }]}>
          {localSyncStatus === "pending" ? "Pending…" : `${uploadProgress}%`}
        </Text>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  overlay: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing[2],
    gap: spacing[1],
  },
  overlayUploading: {
    backgroundColor: "rgba(0,0,0,0.7)",
    paddingHorizontal: spacing[2],
  },
  overlayWifi: {
    backgroundColor: "rgba(0,0,0,0.8)",
  },
  overlayFailed: {
    backgroundColor: "rgba(220,38,38,0.2)",
  },
  progressBar: {
    width: "80%",
    height: 3,
    backgroundColor: colors.neutral[600],
    borderRadius: radii.full,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: radii.full,
  },
  label: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 16,
    textAlign: "center",
  },
  wifiIcon: {
    fontSize: 20,
    lineHeight: 24,
  },
  failedIcon: {
    fontSize: 20,
    lineHeight: 24,
  },
});
