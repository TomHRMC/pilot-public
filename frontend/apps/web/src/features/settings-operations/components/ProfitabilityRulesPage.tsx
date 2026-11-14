/**
 * ProfitabilityRulesPage — FE-B11
 *
 * Settings: H1 (etc_variance_note_required_pct), H2 (profitability_target_margin_pct),
 *           H3 (overhead_allocation_pct) — all save-on-blur
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

const ETC_VARIANCE_KEY = "etc_variance_note_required_pct";
const TARGET_MARGIN_KEY = "profitability_target_margin_pct";
const OVERHEAD_KEY = "overhead_allocation_pct";

export function ProfitabilityRulesPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const etcEntry = getCatalogEntry(ETC_VARIANCE_KEY);
  const targetEntry = getCatalogEntry(TARGET_MARGIN_KEY);
  const overheadEntry = getCatalogEntry(OVERHEAD_KEY);

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
    <div className="space-y-6" data-testid="profitability-rules-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">
          Profitability rules
        </h1>
        <p className="text-caption text-neutral-600">
          Configure rules that determine profitability calculations for your
          jobs.
        </p>
      </div>

      <SettingsSection title="Profitability rules">
        <SettingControl
          settingKey={ETC_VARIANCE_KEY}
          label={etcEntry?.label ?? "ETC variance note required"}
          description={etcEntry?.description}
          value={(etcEntry?.currentEffectiveValue as number | null) ?? 10}
          defaultValue={(etcEntry?.systemDefault as number | null) ?? 10}
          scope={etcEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(ETC_VARIANCE_KEY)}
          onRevert={makeOnRevert(
            ETC_VARIANCE_KEY,
            etcEntry?.systemDefault ?? 10,
          )}
          inputType="integer"
          validationRules={etcEntry?.validationRules ?? { min: 0, max: 100 }}
          unit="%"
          testID="etc-variance-input"
        />

        <SettingControl
          settingKey={TARGET_MARGIN_KEY}
          label={targetEntry?.label ?? "Profitability target margin"}
          description={targetEntry?.description}
          value={(targetEntry?.currentEffectiveValue as number | null) ?? 25}
          defaultValue={(targetEntry?.systemDefault as number | null) ?? 25}
          scope={targetEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(TARGET_MARGIN_KEY)}
          onRevert={makeOnRevert(
            TARGET_MARGIN_KEY,
            targetEntry?.systemDefault ?? 25,
          )}
          inputType="integer"
          validationRules={targetEntry?.validationRules ?? { min: 0, max: 100 }}
          unit="%"
          testID="target-margin-input"
        />

        <SettingControl
          settingKey={OVERHEAD_KEY}
          label={overheadEntry?.label ?? "Overhead allocation rate"}
          description={overheadEntry?.description}
          value={(overheadEntry?.currentEffectiveValue as number | null) ?? 20}
          defaultValue={(overheadEntry?.systemDefault as number | null) ?? 20}
          scope={overheadEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(OVERHEAD_KEY)}
          onRevert={makeOnRevert(
            OVERHEAD_KEY,
            overheadEntry?.systemDefault ?? 20,
          )}
          inputType="integer"
          validationRules={
            overheadEntry?.validationRules ?? { min: 0, max: 100 }
          }
          unit="%"
          testID="overhead-allocation-input"
        />
      </SettingsSection>
    </div>
  );
}
