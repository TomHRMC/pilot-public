import React from "react";
/**
 * SettingsSection — FE-B11
 *
 * Location: apps/web/src/features/settings/components/SettingsSection.tsx
 *
 * Reusable page section wrapper: section heading + vertical list of
 * SettingControl / EffectiveSettingDisplay fields.
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

interface SettingsSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  testID?: string;
}

export function SettingsSection({
  title,
  description,
  children,
  testID,
}: SettingsSectionProps) {
  return (
    <section
      data-testid={
        testID ?? `settings-section-${title.replace(/\s+/g, "-").toLowerCase()}`
      }
      className="space-y-4"
    >
      <div className="border-b border-neutral-200 pb-3">
        <h2 className="text-h3 font-medium text-neutral-900">{title}</h2>
        {description && (
          <p className="mt-1 text-caption text-neutral-600">{description}</p>
        )}
      </div>

      <div className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
        {children}
      </div>
    </section>
  );
}
