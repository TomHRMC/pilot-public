/**
 * DisabledAccountExportScreen — Pending data export when account is disabled
 *
 * Location: apps/mobile/features/offline-sync/components/DisabledAccountExportScreen.tsx
 *
 * Shown when sessionExpiredEmitter fires with reason: 'account_disabled'.
 * Replaces normal login screen.
 *
 * Allows tech to export all pending (unsynced) records as JSON to device
 * via expo-sharing + expo-file-system. NO Pilot API call — account is disabled.
 *
 * Accessibility: role="alert", aria-live="assertive" for the disabled message.
 *
 * Export format per design doc §G.8:
 * {
 *   export_format_version: 1,
 *   exported_at: ISO string,
 *   tenant_id: string,
 *   user_id: string,
 *   records: { time_entries, expenses, photos, change_orders, loto_checks,
 *               job_status_changes, job_notes }
 * }
 *
 * Per batch-fe-b7-design.md Section A.3.6 and §15.12.
 */

import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
// expo-file-system v19 moved legacy APIs (EncodingType, cacheDirectory,
// writeAsStringAsync) to the /legacy sub-path.
// Use /legacy to preserve the v17 API surface without rewriting the export logic.
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";
import { database } from "../../../database";
import type { SyncableModel } from "../../../database/models/SyncableModel";

interface DisabledAccountExportScreenProps {
  userId: string;
  tenantId: string;
  testID?: string;
}

type ExportStatus = "idle" | "exporting" | "exported" | "error";

export function DisabledAccountExportScreen({
  userId,
  tenantId,
  testID,
}: DisabledAccountExportScreenProps): React.ReactElement {
  const [exportStatus, setExportStatus] = useState<ExportStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    setExportStatus("exporting");
    setErrorMessage(null);

    try {
      // Collect all unsynced records from WatermelonDB
      const [
        timeEntries,
        expenses,
        photos,
        changeOrders,
        lotoChecks,
        statusChanges,
        jobNotes,
      ] = await Promise.all([
        database.get<SyncableModel>("time_entries").query().fetch(),
        database.get<SyncableModel>("expenses").query().fetch(),
        database.get<SyncableModel>("photos").query().fetch(),
        database.get<SyncableModel>("change_orders").query().fetch(),
        database.get<SyncableModel>("loto_checks").query().fetch(),
        database.get<SyncableModel>("job_status_changes").query().fetch(),
        database.get<SyncableModel>("job_notes").query().fetch(),
      ]);

      const serializeRecord = (
        record: SyncableModel,
      ): Record<string, unknown> => {
        const raw = (record as unknown as { _raw: Record<string, unknown> })
          ._raw;
        return { ...raw };
      };

      const exportData = {
        export_format_version: 1,
        exported_at: new Date().toISOString(),
        tenant_id: tenantId,
        user_id: userId,
        records: {
          time_entries: timeEntries.map(serializeRecord),
          expenses: expenses.map(serializeRecord),
          photos: photos.map((p) => ({
            ...serializeRecord(p),
            note: "Photo file not included in this export; URI references device storage",
          })),
          change_orders: changeOrders.map(serializeRecord),
          loto_checks: lotoChecks.map(serializeRecord),
          job_status_changes: statusChanges.map(serializeRecord),
          job_notes: jobNotes.map(serializeRecord),
        },
      };

      const jsonString = JSON.stringify(exportData, null, 2);
      const fileName = `pilot-export-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
      const filePath = `${FileSystem.cacheDirectory ?? ""}${fileName}`;

      await FileSystem.writeAsStringAsync(filePath, jsonString, {
        encoding: FileSystem.EncodingType.UTF8,
      });

      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(filePath, {
          mimeType: "application/json",
          dialogTitle: "Export your Pilot data",
        });
      }

      setExportStatus("exported");
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Export failed. Please try again.",
      );
      setExportStatus("error");
    }
  }, [userId, tenantId]);

  return (
    <SafeAreaView
      style={styles.container}
      testID={testID ?? "disabled-account-export-screen"}
    >
      {/* Alert message — assertive for screen readers */}
      <View
        style={styles.alertBox}
        accessible={true}
        accessibilityRole="alert"
        accessibilityLiveRegion="assertive"
        accessibilityLabel="Your account has been disabled"
      >
        <Text style={styles.alertIcon}>🔒</Text>
        <Text style={styles.alertTitle}>Account Disabled</Text>
        <Text style={styles.alertDescription}>
          Your Pilot account has been disabled. Contact your account owner for
          assistance.
        </Text>
      </View>

      {/* Pending data notice */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>You have unsynced data</Text>
        <Text style={styles.sectionDescription}>
          Some of your work was captured offline and has not been synced. Export
          it before you lose access.
        </Text>
      </View>

      {/* Export button */}
      <View style={styles.exportSection}>
        {exportStatus === "error" && errorMessage && (
          <Text style={styles.errorText}>{errorMessage}</Text>
        )}

        {exportStatus === "exported" && (
          <Text style={styles.successText}>✓ Export shared successfully</Text>
        )}

        <Pressable
          onPress={handleExport}
          disabled={exportStatus === "exporting"}
          style={[
            styles.exportButton,
            exportStatus === "exporting" && styles.buttonDisabled,
          ]}
          accessibilityRole="button"
          accessibilityLabel="Export your unsynced data to a file"
          testID="export-button"
        >
          {exportStatus === "exporting" ? (
            <ActivityIndicator size="small" color={colors.neutral[50]} />
          ) : (
            <Text style={styles.exportButtonText}>
              {exportStatus === "exported" ? "Export again" : "Export to file"}
            </Text>
          )}
        </Pressable>
      </View>

      <Text style={styles.footer}>
        Your photos are not included in the export — they remain on your device.
      </Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[900],
    padding: spacing[6],
    gap: spacing[6],
  },
  alertBox: {
    alignItems: "center",
    gap: spacing[3],
    paddingVertical: spacing[6],
  },
  alertIcon: {
    fontSize: 48,
    lineHeight: 56,
  },
  alertTitle: {
    fontSize: mobileFontSizes.h1,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.fault[400],
    lineHeight: 30,
    textAlign: "center",
  },
  alertDescription: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[200],
    lineHeight: 20,
    textAlign: "center",
  },
  section: {
    gap: spacing[2],
  },
  sectionTitle: {
    fontSize: mobileFontSizes.h3,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 24,
  },
  sectionDescription: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  exportSection: {
    gap: spacing[3],
  },
  exportButton: {
    minHeight: touchTargets.mobile.md,
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing[4],
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  exportButtonText: {
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
  errorText: {
    fontSize: mobileFontSizes.body,
    color: colors.fault[400],
    lineHeight: 20,
  },
  successText: {
    fontSize: mobileFontSizes.body,
    color: colors.margin[400],
    lineHeight: 20,
  },
  footer: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[600],
    lineHeight: 16,
    textAlign: "center",
  },
});
