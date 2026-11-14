/**
 * Mobile Sync & Storage settings — FE-B11
 *
 * Location: apps/mobile/app/(tabs)/(home)/settings/sync-storage.tsx
 */

import React from "react";
import {
  ScrollView,
  Text,
  View,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import {
  useMobileSettingsCatalog,
  MOBILE_SETTINGS_CATALOG_QUERY_KEY,
} from "../../../../features/settings/hooks/useMobileSettingsCatalog";
import { BackgroundSyncUserControl } from "../../../../features/settings/components/BackgroundSyncUserControl";
import { SyncStorageSettingsSection } from "../../../../features/settings/components/SyncStorageSettingsSection";
// MOB-B8: Background sync policy section (uses dedicated /background-sync-policy endpoint)
import { BackgroundSyncSettingsSection } from "../../../../features/settings/components/BackgroundSyncSettingsSection";
import { useQueryClient, useMutation } from "@tanstack/react-query";

export default function MobileSyncStorageSettings() {
  const { catalogMap, isLoading, isError, getCatalogEntry } =
    useMobileSettingsCatalog();
  const queryClient = useQueryClient();

  const { mutateAsync: writeUserOverride } = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: unknown }) => {
      const res = await fetch(`/api/v1/settings/${key}/user-override`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!res.ok) throw new Error("Save failed.");
      return res.json();
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: MOBILE_SETTINGS_CATALOG_QUERY_KEY,
      });
    },
  });

  const { mutateAsync: revertUserOverride } = useMutation({
    mutationFn: async (key: string) => {
      const res = await fetch(`/api/v1/settings/${key}/user-override`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Revert failed.");
      return res.json();
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: MOBILE_SETTINGS_CATALOG_QUERY_KEY,
      });
    },
  });

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>
          Failed to load settings. Pull to refresh.
        </Text>
      </View>
    );
  }

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  const syncEnabledEntry = getCatalogEntry("background_sync_enabled");

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="mobile-sync-storage-settings"
    >
      <Text style={styles.heading}>Sync &amp; Storage</Text>

      {syncEnabledEntry && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Your Sync Preference</Text>
          <BackgroundSyncUserControl
            catalogEntry={syncEnabledEntry}
            onSaveUserOverride={async (val: unknown) => {
              await writeUserOverride({
                key: "background_sync_enabled",
                value: val,
              });
            }}
            onRevertUserOverride={async () => {
              await revertUserOverride("background_sync_enabled");
            }}
            testID="mobile-sync-user-control"
          />
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Tenant Sync Settings</Text>
        <Text style={styles.sectionHint}>
          Set by your company — contact your admin to change.
        </Text>
        <SyncStorageSettingsSection
          catalogEntries={catalogMap}
          testID="mobile-sync-storage-section"
        />
      </View>

      {/* MOB-B8: Background sync policy (push interval, wifi-only, battery floor) */}
      <View style={styles.section}>
        <BackgroundSyncSettingsSection testID="mobile-background-sync-section" />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  heading: {
    fontSize: 22,
    fontWeight: "500",
    color: "#111827",
    marginBottom: 8,
  },
  section: { gap: 8 },
  sectionTitle: { fontSize: 14, fontWeight: "600", color: "#374151" },
  sectionHint: { fontSize: 12, color: "#6B7280", marginBottom: 4 },
  errorText: { fontSize: 14, color: "#DC2626" },
});
