/**
 * OperationsSettingsSection — FE-B11 Mobile
 *
 * Location: apps/mobile/features/settings/components/OperationsSettingsSection.tsx
 *
 * Read-only display of tenant-level Operations settings:
 *   - etc_variance_note_required_pct
 *   - require_approval_for_tech_quotes
 *
 * Uses <SettingControl readOnly> with provenance annotation.
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

import React from "react";
import { SettingControl } from "@pilot/ui";
import type { CatalogEntry } from "@pilot/ui";

interface OperationsSettingsSectionProps {
  catalogEntries: Map<string, CatalogEntry>;
  testID?: string;
}

const ETC_VARIANCE_KEY = "etc_variance_note_required_pct";
const APPROVAL_KEY = "require_approval_for_tech_quotes";

export function OperationsSettingsSection({
  catalogEntries,
  testID,
}: OperationsSettingsSectionProps) {
  const etcEntry = catalogEntries.get(ETC_VARIANCE_KEY);
  const approvalEntry = catalogEntries.get(APPROVAL_KEY);

  const getProvenance = (entry?: CatalogEntry): "tenant" | "system" =>
    entry?.currentScope === "tenant" ? "tenant" : "system";

  return (
    <div data-testid={testID ?? "operations-settings-section"}>
      {etcEntry && (
        <SettingControl
          settingKey={ETC_VARIANCE_KEY}
          label={etcEntry.label}
          description={etcEntry.description}
          value={(etcEntry.currentEffectiveValue as number | null) ?? 10}
          defaultValue={(etcEntry.systemDefault as number | null) ?? 10}
          scope={etcEntry.currentScope}
          saveMode="blur"
          onSave={async () => {}}
          readOnly
          inputType="integer"
          unit="%"
          provenanceAnnotation={getProvenance(etcEntry)}
          testID="mobile-etc-variance-display"
        />
      )}

      {approvalEntry && (
        <SettingControl
          settingKey={APPROVAL_KEY}
          label={approvalEntry.label}
          description={approvalEntry.description}
          value={
            (approvalEntry.currentEffectiveValue as boolean | null) ?? false
          }
          defaultValue={
            (approvalEntry.systemDefault as boolean | null) ?? false
          }
          scope={approvalEntry.currentScope}
          saveMode="blur"
          onSave={async () => {}}
          readOnly
          inputType="boolean"
          provenanceAnnotation={getProvenance(approvalEntry)}
          testID="mobile-require-approval-display"
        />
      )}
    </div>
  );
}
