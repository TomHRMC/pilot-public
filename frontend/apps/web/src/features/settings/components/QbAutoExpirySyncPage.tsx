/**
 * QbAutoExpirySyncPage — FE-B11
 *
 * Location: apps/web/src/features/settings/components/QbAutoExpirySyncPage.tsx
 *
 * Settings (Mockup B — save-on-group-complete canonical case):
 *   B1: qb_auto_expire_invoice_enabled (toggle)
 *   B2: qb_auto_expire_invoice_direction (select — required when B1 enabled)
 *   B3: qb_auto_expire_estimate_enabled (toggle)
 *   B4: qb_auto_expire_estimate_direction (select — required when B3 enabled)
 *   B5: qb_invoice_pre_warning_days (blur + cross-field validation)
 *   B6: qb_invoice_auto_expire_days (blur + cross-field validation)
 *   B7: (sync direction pref — future)
 *   B8: (sync direction pref — future)
 *
 * Save-on-group-complete: B1+B2 are a group; B3+B4 are a group.
 * B5+B6 are independent blur fields with cross-field validation.
 */

"use client";

import React from "react";
import {
  SettingControl,
  SaveOnGroupCompleteIndicator,
  useFormSaveStrategy,
  useNotificationQueue,
} from "@pilot/ui";
import type { GroupSaveOptions } from "@pilot/ui";
import { SettingsSection } from "./SettingsSection";
import { useSettingsCatalog } from "../hooks/useSettingsCatalog";
import { useBulkSettingWrite } from "../hooks/useBulkSettingWrite";
import { useTenantSettingWrite } from "../hooks/useTenantSettingWrite";
import { useTenantSettingRevert } from "../hooks/useTenantSettingRevert";
import { notifyReverted, notifySaved } from "../utils/notify";
import { ErrorState } from "@pilot/ui";

const INVOICE_ENABLED_KEY = "qb_auto_expire_invoice_enabled";
const INVOICE_DIRECTION_KEY = "qb_auto_expire_invoice_direction";
const ESTIMATE_ENABLED_KEY = "qb_auto_expire_estimate_enabled";
const ESTIMATE_DIRECTION_KEY = "qb_auto_expire_estimate_direction";
const PRE_WARNING_KEY = "qb_invoice_pre_warning_days";
const AUTO_EXPIRE_KEY = "qb_invoice_auto_expire_days";

const DIRECTION_OPTIONS = [
  { value: "accept_remote", label: "Accept QuickBooks version" },
  { value: "accept_local", label: "Accept Pilot version" },
];

type StringOrBool = string | boolean | null;

export function QbAutoExpirySyncPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: bulkWrite } = useBulkSettingWrite();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const invoiceEnabledEntry = getCatalogEntry(INVOICE_ENABLED_KEY);
  const invoiceDirectionEntry = getCatalogEntry(INVOICE_DIRECTION_KEY);
  const estimateEnabledEntry = getCatalogEntry(ESTIMATE_ENABLED_KEY);
  const estimateDirectionEntry = getCatalogEntry(ESTIMATE_DIRECTION_KEY);
  const preWarningEntry = getCatalogEntry(PRE_WARNING_KEY);
  const autoExpireEntry = getCatalogEntry(AUTO_EXPIRE_KEY);

  // Invoice group (B1 + B2) — save-on-group-complete
  const invoiceGroupSave = useFormSaveStrategy<StringOrBool>({
    mode: "group",
    fields: [
      { key: INVOICE_ENABLED_KEY, required: true },
      {
        key: INVOICE_DIRECTION_KEY,
        required: (vals) => Boolean(vals[INVOICE_ENABLED_KEY]),
      },
    ],
    initialValues: {
      [INVOICE_ENABLED_KEY]:
        (invoiceEnabledEntry?.currentEffectiveValue as boolean | null) ?? false,
      [INVOICE_DIRECTION_KEY]:
        (invoiceDirectionEntry?.currentEffectiveValue as string | null) ?? null,
    },
    onSave: async (values) => {
      const enabled = values[INVOICE_ENABLED_KEY];
      // If disabling, don't require direction
      if (!enabled) {
        await writeSetting({ key: INVOICE_ENABLED_KEY, value: false });
      } else {
        await bulkWrite({
          values: {
            [INVOICE_ENABLED_KEY]: enabled,
            [INVOICE_DIRECTION_KEY]: values[INVOICE_DIRECTION_KEY],
          },
        });
      }
      notifySaved(addNotification, "QB invoice auto-expiry");
    },
    onRollback: () => {},
  } as GroupSaveOptions<StringOrBool>);

  // Estimate group (B3 + B4) — save-on-group-complete
  const estimateGroupSave = useFormSaveStrategy<StringOrBool>({
    mode: "group",
    fields: [
      { key: ESTIMATE_ENABLED_KEY, required: true },
      {
        key: ESTIMATE_DIRECTION_KEY,
        required: (vals) => Boolean(vals[ESTIMATE_ENABLED_KEY]),
      },
    ],
    initialValues: {
      [ESTIMATE_ENABLED_KEY]:
        (estimateEnabledEntry?.currentEffectiveValue as boolean | null) ??
        false,
      [ESTIMATE_DIRECTION_KEY]:
        (estimateDirectionEntry?.currentEffectiveValue as string | null) ??
        null,
    },
    onSave: async (values) => {
      const enabled = values[ESTIMATE_ENABLED_KEY];
      if (!enabled) {
        await writeSetting({ key: ESTIMATE_ENABLED_KEY, value: false });
      } else {
        await bulkWrite({
          values: {
            [ESTIMATE_ENABLED_KEY]: enabled,
            [ESTIMATE_DIRECTION_KEY]: values[ESTIMATE_DIRECTION_KEY],
          },
        });
      }
      notifySaved(addNotification, "QB estimate auto-expiry");
    },
    onRollback: () => {},
  } as GroupSaveOptions<StringOrBool>);

  const invoiceReturn = invoiceGroupSave as {
    groupIsComplete: boolean;
    incompleteFields: string[];
    fieldValues: Record<string, StringOrBool>;
    setFieldValue: (k: string, v: StringOrBool) => void;
    savePending: boolean;
    savedAt: number | null;
    lastError: string | null;
  };

  const estimateReturn = estimateGroupSave as {
    groupIsComplete: boolean;
    incompleteFields: string[];
    fieldValues: Record<string, StringOrBool>;
    setFieldValue: (k: string, v: StringOrBool) => void;
    savePending: boolean;
    savedAt: number | null;
    lastError: string | null;
  };

  if (isError) return <ErrorState type="network" />;
  if (isLoading)
    return <div className="p-6 text-caption text-neutral-400">Loading…</div>;

  const invoiceEnabled = Boolean(
    invoiceReturn.fieldValues[INVOICE_ENABLED_KEY],
  );
  const estimateEnabled = Boolean(
    estimateReturn.fieldValues[ESTIMATE_ENABLED_KEY],
  );

  const preWarningValue =
    (preWarningEntry?.currentEffectiveValue as number | null) ?? 7;
  const autoExpireValue =
    (autoExpireEntry?.currentEffectiveValue as number | null) ?? 30;

  const makeOnRevert =
    (key: string, def: unknown) => async (): Promise<void> => {
      await revertSetting({ key, systemDefault: def });
      notifyReverted(addNotification);
    };

  return (
    <div className="space-y-6" data-testid="qb-auto-expiry-sync-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">
          Auto-expiry &amp; sync
        </h1>
        <p className="text-caption text-neutral-600">
          Configure automatic resolution of QuickBooks sync conflicts.
        </p>
      </div>

      {/* B1 + B2: QB Invoice group */}
      <SettingsSection
        title="Invoice conflicts"
        description="Configure automatic resolution for QB invoice sync conflicts."
      >
        <div
          className={`p-4 space-y-3 ${invoiceReturn.incompleteFields.includes(INVOICE_DIRECTION_KEY) && invoiceEnabled ? "border border-alert-300" : ""}`}
        >
          {/* B1: Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-body font-medium text-neutral-900">
                Auto-expire QB invoices
              </p>
              <p className="text-caption text-neutral-600">
                Automatically resolve QB invoice sync conflicts.
              </p>
            </div>
            <button
              role="switch"
              type="button"
              aria-checked={invoiceEnabled}
              onClick={() =>
                invoiceReturn.setFieldValue(
                  INVOICE_ENABLED_KEY,
                  !invoiceEnabled,
                )
              }
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 ${
                invoiceEnabled ? "bg-brand-600" : "bg-neutral-200"
              }`}
              data-testid="qb-invoice-auto-expire-toggle"
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${invoiceEnabled ? "translate-x-6" : "translate-x-1"}`}
              />
            </button>
          </div>

          {/* B2: Direction (only when enabled) */}
          {invoiceEnabled && (
            <div>
              <label className="block text-caption font-medium text-neutral-900 mb-1">
                Resolution direction
                <span className="ml-1 text-alert-600">(required)</span>
              </label>
              <select
                value={String(
                  invoiceReturn.fieldValues[INVOICE_DIRECTION_KEY] ?? "",
                )}
                onChange={(e) =>
                  invoiceReturn.setFieldValue(
                    INVOICE_DIRECTION_KEY,
                    e.target.value || null,
                  )
                }
                className="w-64 rounded-md border border-neutral-200 bg-white px-3 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
                data-testid="qb-invoice-direction-select"
              >
                <option value="">Pick a direction…</option>
                {DIRECTION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <SaveOnGroupCompleteIndicator
            groupIsComplete={!invoiceEnabled || invoiceReturn.groupIsComplete}
            incompleteFields={invoiceReturn.incompleteFields}
            savedAt={invoiceReturn.savedAt}
            savePending={invoiceReturn.savePending}
            error={invoiceReturn.lastError}
            incompletePrompt="Pick a direction to complete this setting."
            testID="invoice-group-indicator"
          />
        </div>
      </SettingsSection>

      {/* B3 + B4: QB Estimate group */}
      <SettingsSection
        title="Estimate conflicts"
        description="Configure automatic resolution for QB estimate sync conflicts."
      >
        <div
          className={`p-4 space-y-3 ${estimateReturn.incompleteFields.includes(ESTIMATE_DIRECTION_KEY) && estimateEnabled ? "border border-alert-300" : ""}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-body font-medium text-neutral-900">
                Auto-expire QB estimates
              </p>
              <p className="text-caption text-neutral-600">
                Automatically resolve QB estimate sync conflicts.
              </p>
            </div>
            <button
              role="switch"
              type="button"
              aria-checked={estimateEnabled}
              onClick={() =>
                estimateReturn.setFieldValue(
                  ESTIMATE_ENABLED_KEY,
                  !estimateEnabled,
                )
              }
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 ${
                estimateEnabled ? "bg-brand-600" : "bg-neutral-200"
              }`}
              data-testid="qb-estimate-auto-expire-toggle"
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${estimateEnabled ? "translate-x-6" : "translate-x-1"}`}
              />
            </button>
          </div>

          {estimateEnabled && (
            <div>
              <label className="block text-caption font-medium text-neutral-900 mb-1">
                Resolution direction
                <span className="ml-1 text-alert-600">(required)</span>
              </label>
              <select
                value={String(
                  estimateReturn.fieldValues[ESTIMATE_DIRECTION_KEY] ?? "",
                )}
                onChange={(e) =>
                  estimateReturn.setFieldValue(
                    ESTIMATE_DIRECTION_KEY,
                    e.target.value || null,
                  )
                }
                className="w-64 rounded-md border border-neutral-200 bg-white px-3 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
                data-testid="qb-estimate-direction-select"
              >
                <option value="">Pick a direction…</option>
                {DIRECTION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <SaveOnGroupCompleteIndicator
            groupIsComplete={!estimateEnabled || estimateReturn.groupIsComplete}
            incompleteFields={estimateReturn.incompleteFields}
            savedAt={estimateReturn.savedAt}
            savePending={estimateReturn.savePending}
            error={estimateReturn.lastError}
            incompletePrompt="Pick a direction to complete this setting."
            testID="estimate-group-indicator"
          />
        </div>
      </SettingsSection>

      {/* B5 + B6: Pre-warning / auto-expire timing (blur + cross-field validation) */}
      <SettingsSection
        title="Auto-expiry timing"
        description="Configure when QB conflicts auto-expire and when warnings appear."
      >
        <SettingControl
          settingKey={AUTO_EXPIRE_KEY}
          label={autoExpireEntry?.label ?? "QB invoice auto-expiry period"}
          description={autoExpireEntry?.description}
          value={autoExpireValue}
          defaultValue={(autoExpireEntry?.systemDefault as number | null) ?? 30}
          scope={autoExpireEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={async (val): Promise<void> => {
            const v = val as number;
            if (preWarningValue !== null && preWarningValue >= v) {
              throw new Error(
                `Pre-warning period must be less than auto-expiry days (${v}).`,
              );
            }
            await writeSetting({ key: AUTO_EXPIRE_KEY, value: v });
          }}
          onRevert={makeOnRevert(
            AUTO_EXPIRE_KEY,
            autoExpireEntry?.systemDefault ?? 30,
          )}
          inputType="integer"
          validationRules={
            autoExpireEntry?.validationRules ?? { min: 1, max: 365 }
          }
          unit="days"
          effectiveRangeLabel={`Effective: ${autoExpireValue} days · Pre-warning at: ${preWarningValue} days`}
          testID="qb-auto-expire-days-input"
        />

        <SettingControl
          settingKey={PRE_WARNING_KEY}
          label={preWarningEntry?.label ?? "QB invoice pre-warning period"}
          description={preWarningEntry?.description}
          value={preWarningValue}
          defaultValue={(preWarningEntry?.systemDefault as number | null) ?? 7}
          scope={preWarningEntry?.currentScope ?? "system"}
          saveMode="blur"
          onSave={async (val): Promise<void> => {
            const v = val as number;
            if (autoExpireValue !== null && v >= autoExpireValue) {
              throw new Error(
                `Pre-warning period must be less than auto-expiry days (${autoExpireValue}).`,
              );
            }
            await writeSetting({ key: PRE_WARNING_KEY, value: v });
          }}
          onRevert={makeOnRevert(
            PRE_WARNING_KEY,
            preWarningEntry?.systemDefault ?? 7,
          )}
          inputType="integer"
          validationRules={
            preWarningEntry?.validationRules ?? { min: 1, max: 30 }
          }
          unit="days before expiry"
          testID="qb-pre-warning-days-input"
        />
      </SettingsSection>
    </div>
  );
}
