/**
 * BackgroundSyncPage — FE-B11
 *
 * Settings:
 *   C1: background_sync_enabled (EffectiveSettingDisplay — per-user override)
 *   C2: background_sync_wifi_only (SettingControl blur)
 *   C3: background_sync_battery_floor_pct (SettingControl blur)
 *   C4: background_sync_interval_minutes (SettingControl blur)
 */

"use client";

import React from "react";
import {
  SettingControl,
  EffectiveSettingDisplay,
  useNotificationQueue,
} from "@pilot/ui";
import { SettingsSection } from "../../settings/components/SettingsSection";
import { useSettingsCatalog } from "../../settings/hooks/useSettingsCatalog";
import { useTenantSettingWrite } from "../../settings/hooks/useTenantSettingWrite";
import { useTenantSettingRevert } from "../../settings/hooks/useTenantSettingRevert";
import { useUserOverrideWrite } from "../../settings/hooks/useUserOverrideWrite";
import { useUserOverrideRevert } from "../../settings/hooks/useUserOverrideRevert";
import { notifyReverted } from "../../settings/utils/notify";
import { ErrorState } from "@pilot/ui";

const SYNC_ENABLED_KEY = "background_sync_enabled";
const WIFI_ONLY_KEY = "background_sync_wifi_only";
const BATTERY_KEY = "background_sync_battery_floor_pct";
const INTERVAL_KEY = "background_sync_interval_minutes";

export function BackgroundSyncPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { mutateAsync: writeUserOverride } = useUserOverrideWrite();
  const { mutateAsync: revertUserOverride } = useUserOverrideRevert();
  const { addNotification } = useNotificationQueue();

  const syncEnabledEntry = getCatalogEntry(SYNC_ENABLED_KEY);
  const wifiOnlyEntry = getCatalogEntry(WIFI_ONLY_KEY);
  const batteryEntry = getCatalogEntry(BATTERY_KEY);
  const intervalEntry = getCatalogEntry(INTERVAL_KEY);

  if (isError) return <ErrorState type="network" />;
  if (isLoading)
    return <div className="p-6 text-caption text-neutral-400">Loading…</div>;

  const makeOnSave =
    (key: string) =>
    async (val: unknown): Promise<void> => {
      await writeSetting({ key, value: val });
    };

  const makeOnRevert =
    (key: string, def: unknown) => async (): Promise<void> => {
      await revertSetting({ key, systemDefault: def });
      notifyReverted(addNotification);
    };

  const syncCurrentValue =
    (syncEnabledEntry?.currentEffectiveValue as boolean | null) ?? true;
  const syncScope = syncEnabledEntry?.currentScope ?? "system";

  return (
    <div className="space-y-6" data-testid="background-sync-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">
          Background sync
        </h1>
        <p className="text-caption text-neutral-600">
          Configure how and when Pilot syncs data in the background.
        </p>
      </div>

      <SettingsSection title="Sync toggle">
        <EffectiveSettingDisplay
          settingKey={SYNC_ENABLED_KEY}
          label={syncEnabledEntry?.label ?? "Background sync"}
          description={syncEnabledEntry?.description}
          tiers={{
            system: {
              value: syncEnabledEntry?.systemDefault ?? true,
              exists: true,
            },
            tenant: {
              value: syncScope === "tenant" ? syncCurrentValue : null,
              exists: syncScope === "tenant",
            },
            user: {
              value: syncScope === "user" ? syncCurrentValue : null,
              exists: syncScope === "user",
            },
          }}
          activeTier={syncScope}
          userCanEdit
          allowsUserOverride={syncEnabledEntry?.allowsUserOverride ?? true}
          onSaveUserOverride={async (val): Promise<void> => {
            await writeUserOverride({ key: SYNC_ENABLED_KEY, value: val });
          }}
          onRevertUserOverride={async (): Promise<void> => {
            await revertUserOverride({
              key: SYNC_ENABLED_KEY,
              tenantDefault:
                syncScope === "tenant"
                  ? syncCurrentValue
                  : (syncEnabledEntry?.systemDefault ?? true),
            });
          }}
          inputType="boolean"
          displayMode="web"
          testID="sync-enabled-display"
        />
      </SettingsSection>

      <SettingsSection title="Sync behavior">
        <SettingControl
          settingKey={WIFI_ONLY_KEY}
          label={wifiOnlyEntry?.label ?? "Sync on Wi-Fi only"}
          description={wifiOnlyEntry?.description}
          value={
            (wifiOnlyEntry?.currentEffectiveValue as boolean | null) ?? true
          }
          defaultValue={
            (wifiOnlyEntry?.systemDefault as boolean | null) ?? true
          }
          scope={wifiOnlyEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(WIFI_ONLY_KEY)}
          onRevert={makeOnRevert(
            WIFI_ONLY_KEY,
            wifiOnlyEntry?.systemDefault ?? true,
          )}
          inputType="boolean"
          testID="wifi-only-toggle"
        />

        <SettingControl
          settingKey={BATTERY_KEY}
          label={batteryEntry?.label ?? "Minimum battery for sync"}
          description={batteryEntry?.description}
          value={(batteryEntry?.currentEffectiveValue as number | null) ?? 20}
          defaultValue={(batteryEntry?.systemDefault as number | null) ?? 20}
          scope={batteryEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(BATTERY_KEY)}
          onRevert={makeOnRevert(
            BATTERY_KEY,
            batteryEntry?.systemDefault ?? 20,
          )}
          inputType="integer"
          validationRules={batteryEntry?.validationRules ?? { min: 5, max: 50 }}
          unit="%"
          testID="battery-floor-input"
        />

        <SettingControl
          settingKey={INTERVAL_KEY}
          label={intervalEntry?.label ?? "Background sync interval"}
          description={intervalEntry?.description}
          value={(intervalEntry?.currentEffectiveValue as number | null) ?? 15}
          defaultValue={(intervalEntry?.systemDefault as number | null) ?? 15}
          scope={intervalEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(INTERVAL_KEY)}
          onRevert={makeOnRevert(
            INTERVAL_KEY,
            intervalEntry?.systemDefault ?? 15,
          )}
          inputType="integer"
          validationRules={
            intervalEntry?.validationRules ?? { min: 5, max: 120 }
          }
          unit="minutes"
          testID="sync-interval-input"
        />
      </SettingsSection>
    </div>
  );
}
