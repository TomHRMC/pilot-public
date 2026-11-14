/**
 * PhotosPage — FE-B11
 *
 * Settings: E1 (photo_upload_wifi_only), E2 (photo_max_resolution_px) — both blur
 */

"use client";

import React from "react";
import { SettingControl, useNotificationQueue } from "@pilot/ui";
import { SettingsSection } from "../../settings/components/SettingsSection";
import { useSettingsCatalog } from "../../settings/hooks/useSettingsCatalog";
import { useTenantSettingWrite } from "../../settings/hooks/useTenantSettingWrite";
import { useTenantSettingRevert } from "../../settings/hooks/useTenantSettingRevert";
import { notifyReverted } from "../../settings/utils/notify";
import { ErrorState } from "@pilot/ui";

const WIFI_KEY = "photo_upload_wifi_only";
const RESOLUTION_KEY = "photo_max_resolution_px";

export function PhotosPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const wifiEntry = getCatalogEntry(WIFI_KEY);
  const resEntry = getCatalogEntry(RESOLUTION_KEY);

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

  return (
    <div className="space-y-6" data-testid="photos-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">Photos</h1>
        <p className="text-caption text-neutral-600">
          Configure photo upload behavior for your team.
        </p>
      </div>

      <SettingsSection title="Photo upload settings">
        <SettingControl
          settingKey={WIFI_KEY}
          label={wifiEntry?.label ?? "Upload photos on Wi-Fi only"}
          description={wifiEntry?.description}
          value={(wifiEntry?.currentEffectiveValue as boolean | null) ?? true}
          defaultValue={(wifiEntry?.systemDefault as boolean | null) ?? true}
          scope={wifiEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(WIFI_KEY)}
          onRevert={makeOnRevert(WIFI_KEY, wifiEntry?.systemDefault ?? true)}
          inputType="boolean"
          testID="photo-wifi-only-toggle"
        />

        <SettingControl
          settingKey={RESOLUTION_KEY}
          label={resEntry?.label ?? "Maximum photo resolution"}
          description={resEntry?.description}
          value={(resEntry?.currentEffectiveValue as number | null) ?? 2048}
          defaultValue={(resEntry?.systemDefault as number | null) ?? 2048}
          scope={resEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(RESOLUTION_KEY)}
          onRevert={makeOnRevert(
            RESOLUTION_KEY,
            resEntry?.systemDefault ?? 2048,
          )}
          inputType="integer"
          validationRules={resEntry?.validationRules ?? { min: 720, max: 4096 }}
          unit="px"
          testID="photo-resolution-input"
        />
      </SettingsSection>
    </div>
  );
}
