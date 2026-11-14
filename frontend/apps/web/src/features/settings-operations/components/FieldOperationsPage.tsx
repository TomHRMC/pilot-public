/**
 * FieldOperationsPage — FE-B11
 *
 * Settings:
 *   I1: default_labor_rate_preset (preset-select, blur)
 *   I2: require_approval_for_tech_quotes (boolean, blur + pending-quote confirmation E.9)
 *   I3: field_notes_required (boolean, blur)
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

const LABOR_RATE_KEY = "default_labor_rate_preset";
const APPROVAL_KEY = "require_approval_for_tech_quotes";
const FIELD_NOTES_KEY = "field_notes_required";

export function FieldOperationsPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const [pendingQuoteConfirm, setPendingQuoteConfirm] = React.useState<{
    pendingCount: number;
    onConfirm: () => void;
  } | null>(null);

  const laborEntry = getCatalogEntry(LABOR_RATE_KEY);
  const approvalEntry = getCatalogEntry(APPROVAL_KEY);
  const fieldNotesEntry = getCatalogEntry(FIELD_NOTES_KEY);

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

  const handleSaveApproval = async (val: unknown): Promise<void> => {
    const res = await writeSetting({ key: APPROVAL_KEY, value: val });
    const pendingCount = (res as { pending_quote_count?: number })
      ?.pending_quote_count;
    if (val === false && pendingCount && pendingCount > 0) {
      await new Promise<void>((resolve) => {
        setPendingQuoteConfirm({
          pendingCount,
          onConfirm: () => {
            setPendingQuoteConfirm(null);
            resolve();
          },
        });
      });
    }
  };

  return (
    <div className="space-y-6" data-testid="field-operations-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">
          Field operations
        </h1>
        <p className="text-caption text-neutral-600">
          Configure defaults and rules for field operations.
        </p>
      </div>

      {pendingQuoteConfirm && (
        <div
          className="rounded-md border border-alert-200 bg-alert-50 p-4"
          role="alert"
          data-testid="pending-quote-confirm-banner"
        >
          <p className="text-body text-alert-700">
            {pendingQuoteConfirm.pendingCount} quote
            {pendingQuoteConfirm.pendingCount !== 1 ? "s are" : " is"} currently
            pending your approval. Disabling this won&apos;t auto-send them —
            they&apos;ll return to draft.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => setPendingQuoteConfirm(null)}
              className="rounded-md border border-neutral-200 px-3 py-1 text-caption text-neutral-700 hover:bg-neutral-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={pendingQuoteConfirm.onConfirm}
              className="rounded-md bg-alert-600 px-3 py-1 text-caption font-medium text-white hover:bg-alert-700"
            >
              Disable anyway
            </button>
          </div>
        </div>
      )}

      <SettingsSection title="Field operations">
        <SettingControl
          settingKey={LABOR_RATE_KEY}
          label={laborEntry?.label ?? "Default labor rate preset"}
          description={laborEntry?.description}
          value={
            (laborEntry?.currentEffectiveValue as string | null) ?? "standard"
          }
          defaultValue={
            (laborEntry?.systemDefault as string | null) ?? "standard"
          }
          scope={laborEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(LABOR_RATE_KEY)}
          onRevert={makeOnRevert(
            LABOR_RATE_KEY,
            laborEntry?.systemDefault ?? "standard",
          )}
          inputType="preset-select"
          selectOptions={[
            { value: "standard", label: "Standard", recommended: true },
            { value: "overtime", label: "Overtime" },
            { value: "emergency", label: "Emergency" },
          ]}
          testID="labor-rate-preset-input"
        />

        <SettingControl
          settingKey={APPROVAL_KEY}
          label={
            approvalEntry?.label ?? "Require approval for technician quotes"
          }
          description={approvalEntry?.description}
          value={
            (approvalEntry?.currentEffectiveValue as boolean | null) ?? false
          }
          defaultValue={
            (approvalEntry?.systemDefault as boolean | null) ?? false
          }
          scope={approvalEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={handleSaveApproval}
          onRevert={makeOnRevert(
            APPROVAL_KEY,
            approvalEntry?.systemDefault ?? false,
          )}
          inputType="boolean"
          testID="require-approval-toggle"
        />

        <SettingControl
          settingKey={FIELD_NOTES_KEY}
          label={fieldNotesEntry?.label ?? "Field notes required on job close"}
          description={fieldNotesEntry?.description}
          value={
            (fieldNotesEntry?.currentEffectiveValue as boolean | null) ?? false
          }
          defaultValue={
            (fieldNotesEntry?.systemDefault as boolean | null) ?? false
          }
          scope={fieldNotesEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={makeOnSave(FIELD_NOTES_KEY)}
          onRevert={makeOnRevert(
            FIELD_NOTES_KEY,
            fieldNotesEntry?.systemDefault ?? false,
          )}
          inputType="boolean"
          testID="field-notes-required-toggle"
        />
      </SettingsSection>
    </div>
  );
}
