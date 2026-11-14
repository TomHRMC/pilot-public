/**
 * OfflineLimitsPage — FE-B11
 *
 * Settings: D1 (offline_hard_limit_hours — blur)
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

const OFFLINE_LIMIT_KEY = "offline_hard_limit_hours";

export function OfflineLimitsPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const entry = getCatalogEntry(OFFLINE_LIMIT_KEY);

  if (isError) return <ErrorState type="network" />;
  if (isLoading)
    return <div className="p-6 text-caption text-neutral-400">Loading…</div>;

  return (
    <div className="space-y-6" data-testid="offline-limits-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">Offline limits</h1>
        <p className="text-caption text-neutral-600">
          Configure how long offline data is retained before a forced sync is
          required.
        </p>
      </div>

      <SettingsSection title="Offline data retention">
        <SettingControl
          settingKey={OFFLINE_LIMIT_KEY}
          label={entry?.label ?? "Offline data retention limit"}
          description={entry?.description}
          value={(entry?.currentEffectiveValue as number | null) ?? 48}
          defaultValue={(entry?.systemDefault as number | null) ?? 48}
          scope={entry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={async (val): Promise<void> => {
            await writeSetting({ key: OFFLINE_LIMIT_KEY, value: val });
          }}
          onRevert={async (): Promise<void> => {
            await revertSetting({
              key: OFFLINE_LIMIT_KEY,
              systemDefault: entry?.systemDefault ?? 48,
            });
            notifyReverted(addNotification);
          }}
          inputType="integer"
          validationRules={entry?.validationRules ?? { min: 1, max: 168 }}
          unit="hours"
          testID="offline-limit-input"
        />
      </SettingsSection>
    </div>
  );
}
