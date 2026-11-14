/**
 * VoicePersonaSection — FE-B11 Mobile
 *
 * Location: apps/mobile/features/settings/components/VoicePersonaSection.tsx
 *
 * voice_persona_tone per-user override using <EffectiveSettingDisplay> in mobile mode.
 * Editable if tenant allows per-user override.
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

import React from "react";
import { EffectiveSettingDisplay } from "@pilot/ui";
import type { CatalogEntry } from "@pilot/ui";

interface VoicePersonaSectionProps {
  catalogEntry?: CatalogEntry;
  onSaveUserOverride: (value: unknown) => Promise<void>;
  onRevertUserOverride: () => Promise<void>;
  testID?: string;
}

const VOICE_PERSONA_OPTIONS = [
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "concise", label: "Concise" },
];

export function VoicePersonaSection({
  catalogEntry,
  onSaveUserOverride,
  onRevertUserOverride,
  testID,
}: VoicePersonaSectionProps) {
  if (!catalogEntry) return null;

  const scope = catalogEntry.currentScope;
  const currentValue =
    (catalogEntry.currentEffectiveValue as string | null) ?? "professional";

  return (
    <EffectiveSettingDisplay
      settingKey="voice_persona_tone"
      label={catalogEntry.label ?? "Voice persona tone"}
      description={catalogEntry.description}
      tiers={{
        system: {
          value:
            (catalogEntry.systemDefault as string | null) ?? "professional",
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
      inputType="select"
      selectOptions={VOICE_PERSONA_OPTIONS}
      displayMode="mobile"
      testID={testID ?? "voice-persona-section"}
    />
  );
}
