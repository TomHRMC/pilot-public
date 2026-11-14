/**
 * VoiceCapturePage — FE-B11
 *
 * Settings: F1 (voice_capture_auto_delete_days — blur)
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

const VOICE_CAPTURE_KEY = "voice_capture_auto_delete_days";

export function VoiceCapturePage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const entry = getCatalogEntry(VOICE_CAPTURE_KEY);

  if (isError) return <ErrorState type="network" />;
  if (isLoading)
    return <div className="p-6 text-caption text-neutral-400">Loading…</div>;

  return (
    <div className="space-y-6" data-testid="voice-capture-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">Voice capture</h1>
        <p className="text-caption text-neutral-600">
          Configure how long voice capture recordings are retained.
        </p>
      </div>

      <SettingsSection title="Voice capture retention">
        <SettingControl
          settingKey={VOICE_CAPTURE_KEY}
          label={entry?.label ?? "Voice capture retention"}
          description={entry?.description}
          value={(entry?.currentEffectiveValue as number | null) ?? 90}
          defaultValue={(entry?.systemDefault as number | null) ?? 90}
          scope={entry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={async (val): Promise<void> => {
            await writeSetting({ key: VOICE_CAPTURE_KEY, value: val });
          }}
          onRevert={async (): Promise<void> => {
            await revertSetting({
              key: VOICE_CAPTURE_KEY,
              systemDefault: entry?.systemDefault ?? 90,
            });
            notifyReverted(addNotification);
          }}
          inputType="integer"
          validationRules={entry?.validationRules ?? { min: 1, max: 365 }}
          unit="days"
          testID="voice-capture-retention-input"
        />
      </SettingsSection>
    </div>
  );
}
