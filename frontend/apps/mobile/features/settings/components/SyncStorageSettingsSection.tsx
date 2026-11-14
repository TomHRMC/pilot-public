/**
 * SyncStorageSettingsSection — FE-B11 Mobile
 *
 * Location: apps/mobile/features/settings/components/SyncStorageSettingsSection.tsx
 *
 * Read-only display of tenant-level Sync & Storage settings:
 *   - background_sync_wifi_only (read-only, provenance: tenant/system)
 *   - background_sync_battery_floor_pct (read-only)
 *   - offline_hard_limit_hours (read-only)
 *   - photo_upload_wifi_only (read-only)
 *
 * Uses <SettingControl readOnly> with provenance annotation (Decision 5).
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

import React from "react";
import { SettingControl } from "@pilot/ui";
import type { CatalogEntry } from "@pilot/ui";

interface SyncStorageSettingsSectionProps {
  catalogEntries: Map<string, CatalogEntry>;
  testID?: string;
}

const WIFI_ONLY_KEY = "background_sync_wifi_only";
const BATTERY_KEY = "background_sync_battery_floor_pct";
const OFFLINE_LIMIT_KEY = "offline_hard_limit_hours";
const PHOTO_WIFI_KEY = "photo_upload_wifi_only";

export function SyncStorageSettingsSection({
  catalogEntries,
  testID,
}: SyncStorageSettingsSectionProps) {
  const wifiEntry = catalogEntries.get(WIFI_ONLY_KEY);
  const batteryEntry = catalogEntries.get(BATTERY_KEY);
  const offlineEntry = catalogEntries.get(OFFLINE_LIMIT_KEY);
  const photoWifiEntry = catalogEntries.get(PHOTO_WIFI_KEY);

  const getProvenance = (entry?: CatalogEntry): "tenant" | "system" =>
    entry?.currentScope === "tenant" ? "tenant" : "system";

  return (
    <div data-testid={testID ?? "sync-storage-settings-section"}>
      {wifiEntry && (
        <SettingControl
          settingKey={WIFI_ONLY_KEY}
          label={wifiEntry.label}
          description={wifiEntry.description}
          value={(wifiEntry.currentEffectiveValue as boolean | null) ?? true}
          defaultValue={(wifiEntry.systemDefault as boolean | null) ?? true}
          scope={wifiEntry.currentScope}
          saveMode="blur"
          onSave={async () => {}}
          readOnly
          inputType="boolean"
          provenanceAnnotation={getProvenance(wifiEntry)}
          testID="mobile-wifi-only-display"
        />
      )}

      {batteryEntry && (
        <SettingControl
          settingKey={BATTERY_KEY}
          label={batteryEntry.label}
          description={batteryEntry.description}
          value={(batteryEntry.currentEffectiveValue as number | null) ?? 20}
          defaultValue={(batteryEntry.systemDefault as number | null) ?? 20}
          scope={batteryEntry.currentScope}
          saveMode="blur"
          onSave={async () => {}}
          readOnly
          inputType="integer"
          unit="%"
          provenanceAnnotation={getProvenance(batteryEntry)}
          testID="mobile-battery-floor-display"
        />
      )}

      {offlineEntry && (
        <SettingControl
          settingKey={OFFLINE_LIMIT_KEY}
          label={offlineEntry.label}
          description={offlineEntry.description}
          value={(offlineEntry.currentEffectiveValue as number | null) ?? 48}
          defaultValue={(offlineEntry.systemDefault as number | null) ?? 48}
          scope={offlineEntry.currentScope}
          saveMode="blur"
          onSave={async () => {}}
          readOnly
          inputType="integer"
          unit="hours"
          provenanceAnnotation={getProvenance(offlineEntry)}
          testID="mobile-offline-limit-display"
        />
      )}

      {photoWifiEntry && (
        <SettingControl
          settingKey={PHOTO_WIFI_KEY}
          label={photoWifiEntry.label}
          description={photoWifiEntry.description}
          value={
            (photoWifiEntry.currentEffectiveValue as boolean | null) ?? true
          }
          defaultValue={
            (photoWifiEntry.systemDefault as boolean | null) ?? true
          }
          scope={photoWifiEntry.currentScope}
          saveMode="blur"
          onSave={async () => {}}
          readOnly
          inputType="boolean"
          provenanceAnnotation={getProvenance(photoWifiEntry)}
          testID="mobile-photo-wifi-display"
        />
      )}
    </div>
  );
}
