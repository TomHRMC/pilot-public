/**
 * MarginBucketsPage — FE-B11
 *
 * Settings: G1 (margin_bucket_boundaries — explicit save + monotonicity validation),
 *           G2 (low_margin_threshold_pct — save-on-blur)
 */

"use client";

import React from "react";
import {
  SettingControl,
  useFormSaveStrategy,
  useNotificationQueue,
} from "@pilot/ui";
import type { ExplicitSaveOptions } from "@pilot/ui";
import { SettingsSection } from "../../settings/components/SettingsSection";
import { useSettingsCatalog } from "../../settings/hooks/useSettingsCatalog";
import { useTenantSettingWrite } from "../../settings/hooks/useTenantSettingWrite";
import { useTenantSettingRevert } from "../../settings/hooks/useTenantSettingRevert";
import { notifyReverted, notifySaved } from "../../settings/utils/notify";
import { ErrorState } from "@pilot/ui";

const BOUNDARIES_KEY = "margin_bucket_boundaries";
const LOW_MARGIN_KEY = "low_margin_threshold_pct";

export function MarginBucketsPage() {
  const { getCatalogEntry, isLoading, isError } = useSettingsCatalog();
  const { mutateAsync: writeSetting } = useTenantSettingWrite();
  const { mutateAsync: revertSetting } = useTenantSettingRevert();
  const { addNotification } = useNotificationQueue();

  const boundariesEntry = getCatalogEntry(BOUNDARIES_KEY);
  const lowMarginEntry = getCatalogEntry(LOW_MARGIN_KEY);

  const initialBoundaries = (boundariesEntry?.currentEffectiveValue as
    | number[]
    | null) ?? [10, 20, 30];

  const [localBoundaries, setLocalBoundaries] =
    React.useState<number[]>(initialBoundaries);
  const [monotonError, setMonotonError] = React.useState<string | null>(null);

  const explicitSave = useFormSaveStrategy<number[]>({
    mode: "explicit",
    initialValues: { [BOUNDARIES_KEY]: initialBoundaries },
    onSave: async (values) => {
      await writeSetting({
        key: BOUNDARIES_KEY,
        value: values[BOUNDARIES_KEY],
      });
      notifySaved(addNotification, "Margin bucket thresholds");
    },
  } as ExplicitSaveOptions<number[]>);

  const isMonotonicallyAscending = (arr: number[]): boolean => {
    for (let i = 1; i < arr.length; i++) {
      if (arr[i] <= arr[i - 1]) return false;
    }
    return true;
  };

  const explicitReturn = explicitSave as {
    isDirty: boolean;
    handleSave: () => Promise<void>;
    handleDiscard: () => void;
    savePending: boolean;
    lastError: string | null;
    setFieldValue: (k: string, v: number[]) => void;
  };

  const handleBoundaryChange = (index: number, val: string) => {
    const num = parseInt(val, 10);
    if (isNaN(num)) return;
    const next = [...localBoundaries];
    next[index] = num;
    setLocalBoundaries(next);
    explicitReturn.setFieldValue(BOUNDARIES_KEY, next);
    setMonotonError(
      isMonotonicallyAscending(next)
        ? null
        : "Thresholds must be in ascending order.",
    );
  };

  const handleAddBoundary = () => {
    const last = localBoundaries[localBoundaries.length - 1] ?? 0;
    const next = [...localBoundaries, last + 10];
    setLocalBoundaries(next);
    explicitReturn.setFieldValue(BOUNDARIES_KEY, next);
  };

  const handleRemoveBoundary = (index: number) => {
    const next = localBoundaries.filter((_, i) => i !== index);
    setLocalBoundaries(next);
    explicitReturn.setFieldValue(BOUNDARIES_KEY, next);
    setMonotonError(
      isMonotonicallyAscending(next)
        ? null
        : "Thresholds must be in ascending order.",
    );
  };

  if (isError) return <ErrorState type="network" />;

  return (
    <div className="space-y-6" data-testid="margin-buckets-page">
      <div>
        <h1 className="text-h2 font-medium text-neutral-900">Margin buckets</h1>
        <p className="text-caption text-neutral-600">
          Configure the thresholds that define job margin performance buckets.
        </p>
      </div>

      <SettingsSection title="Margin bucket thresholds">
        <div className="p-4 space-y-3" data-testid="margin-boundaries-editor">
          <label className="block text-body font-medium text-neutral-900">
            Bucket boundary thresholds
          </label>
          <p className="text-caption text-neutral-600">
            Percentage boundaries that define margin performance buckets. Values
            must be strictly ascending.
          </p>
          {localBoundaries.map((val, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="w-16 text-caption text-neutral-600">
                Bucket {idx + 1}
              </span>
              <input
                type="number"
                value={val}
                onChange={(e) => handleBoundaryChange(idx, e.target.value)}
                min={0}
                max={100}
                className={`w-20 rounded-md border bg-white px-3 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 ${
                  monotonError ? "border-fault-200" : "border-neutral-200"
                }`}
                data-testid={`boundary-input-${idx}`}
              />
              <span className="text-body text-neutral-600">%</span>
              {localBoundaries.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveBoundary(idx)}
                  className="text-caption text-fault-600 hover:text-fault-800"
                  aria-label={`Remove bucket ${idx + 1}`}
                >
                  Remove
                </button>
              )}
            </div>
          ))}

          <button
            type="button"
            onClick={handleAddBoundary}
            className="text-caption text-brand-600 hover:text-brand-800"
          >
            + Add bucket
          </button>

          {monotonError && (
            <p role="alert" className="text-caption text-fault-600">
              {monotonError}
            </p>
          )}

          <div className="flex items-center gap-3 border-t border-neutral-200 pt-3">
            <button
              type="button"
              disabled={
                !explicitReturn.isDirty ||
                !!monotonError ||
                explicitReturn.savePending
              }
              onClick={explicitReturn.handleSave}
              className="rounded-md bg-brand-600 px-4 py-2 text-caption font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              data-testid="margin-boundaries-save-btn"
            >
              {explicitReturn.savePending ? "Saving…" : "Save thresholds"}
            </button>
            <button
              type="button"
              disabled={!explicitReturn.isDirty}
              onClick={explicitReturn.handleDiscard}
              className="rounded-md border border-neutral-200 px-4 py-2 text-caption text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
            >
              Discard
            </button>
          </div>

          {explicitReturn.lastError && (
            <p role="alert" className="text-caption text-fault-600">
              {explicitReturn.lastError}
            </p>
          )}
        </div>
      </SettingsSection>

      <SettingsSection title="Low-margin alert">
        {isLoading ? (
          <div className="p-4 text-caption text-neutral-400">Loading…</div>
        ) : (
          <SettingControl
            settingKey={LOW_MARGIN_KEY}
            label="Low-margin alert threshold"
            description="Jobs below this margin % trigger a low-margin alert."
            value={
              (lowMarginEntry?.currentEffectiveValue as number | null) ?? 15
            }
            defaultValue={
              (lowMarginEntry?.systemDefault as number | null) ?? 15
            }
            scope={lowMarginEntry?.currentScope ?? "system"}
            saveMode="blur"
            onSave={async (val): Promise<void> => {
              await writeSetting({ key: LOW_MARGIN_KEY, value: val });
            }}
            onRevert={async (): Promise<void> => {
              await revertSetting({
                key: LOW_MARGIN_KEY,
                systemDefault: lowMarginEntry?.systemDefault ?? 15,
              });
              notifyReverted(addNotification);
            }}
            inputType="integer"
            validationRules={
              lowMarginEntry?.validationRules ?? { min: 0, max: 100 }
            }
            unit="%"
            testID="low-margin-threshold-input"
          />
        )}
      </SettingsSection>
    </div>
  );
}
