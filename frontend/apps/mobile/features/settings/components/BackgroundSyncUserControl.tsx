/**
 * BackgroundSyncUserControl — FE-B11 Mobile
 *
 * Location: apps/mobile/features/settings/components/BackgroundSyncUserControl.tsx
 *
 * background_sync_enabled per-user override using <EffectiveSettingDisplay> in mobile mode.
 * Editable if tenant allows per-user override (allowsUserOverride=true).
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

import React from "react";
import { EffectiveSettingDisplay } from "@pilot/ui";
import type { CatalogEntry } from "@pilot/ui";

interface BackgroundSyncUserControlProps {
  catalogEntry?: CatalogEntry;
  onSaveUserOverride: (value: unknown) => Promise<void>;
  onRevertUserOverride: () => Promise<void>;
  testID?: string;
}

export function BackgroundSyncUserControl({
  catalogEntry,
  onSaveUserOverride,
  onRevertUserOverride,
  testID,
}: BackgroundSyncUserControlProps) {
  if (!catalogEntry) return null;

  const scope = catalogEntry.currentScope;
  const currentValue =
    (catalogEntry.currentEffectiveValue as boolean | null) ?? true;

  return (
    <EffectiveSettingDisplay
      settingKey="background_sync_enabled"
      label={catalogEntry.label}
      description={catalogEntry.description}
      tiers={{
        system: {
          value: (catalogEntry.systemDefault as boolean | null) ?? true,
          exists: true,
        },
        tenant: {
          value: scope === "tenant" ? currentValue : null,
          exists: scope === "tenant",
        },
        user: {
          value: scope === "user" ? currentValue : null,
          exists: scope === "user",
        },
      }}
      activeTier={scope}
      userCanEdit={catalogEntry.allowsUserOverride}
      allowsUserOverride={catalogEntry.allowsUserOverride}
      onSaveUserOverride={onSaveUserOverride}
      onRevertUserOverride={onRevertUserOverride}
      inputType="boolean"
      displayMode="mobile"
      testID={testID ?? "background-sync-user-control"}
    />
  );
}
