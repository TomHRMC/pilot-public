/**
 * CalendarAutoExpirySettings — two-tier auto-expiry configuration
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarAutoExpirySettings.tsx
 *
 * FE-B11 Migration: now uses <SettingControl> from @pilot/ui instead of the
 * local BaseSettingInput stub. Wired to useSettingsCatalog for live scope/defaultValue.
 *
 * Two integer fields:
 *   calendar_conflict_auto_expire_days (default: 30) — days until auto-resolution
 *   calendar_conflict_pre_warning_days (default: 7) — days before warning badge shows
 *
 * Cross-field validation: pre_warning_days must be < auto_expire_days.
 * Save mode: 'blur' for both fields.
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

"use client";

import React from "react";
import { SettingControl } from "@pilot/ui";
import type { CatalogEntry } from "@pilot/ui";

const AUTO_EXPIRE_KEY = "calendar_conflict_auto_expire_days";
const PRE_WARNING_KEY = "calendar_conflict_pre_warning_days";

const SYSTEM_DEFAULT_AUTO_EXPIRE = 30;
const SYSTEM_DEFAULT_PRE_WARNING = 7;

interface CalendarAutoExpirySettingsProps {
  /** Catalog entries for the two settings — sourced from useSettingsCatalog */
  autoExpiryCatalogEntry?: CatalogEntry;
  preWarningCatalogEntry?: CatalogEntry;
  /** Async save callback — wired to useTenantSettingWrite */
  onSaveAutoExpiry?: (value: number | null) => Promise<void>;
  onSavePreWarning?: (value: number | null) => Promise<void>;
  /** Async revert callbacks — wired to useTenantSettingRevert */
  onRevertAutoExpiry?: () => Promise<void>;
  onRevertPreWarning?: () => Promise<void>;
  testID?: string;
}

export function CalendarAutoExpirySettings({
  autoExpiryCatalogEntry,
  preWarningCatalogEntry,
  onSaveAutoExpiry,
  onSavePreWarning,
  onRevertAutoExpiry,
  onRevertPreWarning,
  testID,
}: CalendarAutoExpirySettingsProps) {
  const [crossFieldError, setCrossFieldError] = React.useState<string | null>(
    null,
  );

  const autoExpireValue =
    (autoExpiryCatalogEntry?.currentEffectiveValue as number | null) ??
    SYSTEM_DEFAULT_AUTO_EXPIRE;
  const preWarningValue =
    (preWarningCatalogEntry?.currentEffectiveValue as number | null) ??
    SYSTEM_DEFAULT_PRE_WARNING;

  const autoExpireScope = autoExpiryCatalogEntry?.currentScope ?? "system";
  const preWarningScope = preWarningCatalogEntry?.currentScope ?? "system";

  const autoExpireDefault =
    (autoExpiryCatalogEntry?.systemDefault as number | null) ??
    SYSTEM_DEFAULT_AUTO_EXPIRE;
  const preWarningDefault =
    (preWarningCatalogEntry?.systemDefault as number | null) ??
    SYSTEM_DEFAULT_PRE_WARNING;

  const handleSaveAutoExpiry = async (value: number | null) => {
    if (
      value !== null &&
      preWarningValue !== null &&
      preWarningValue >= value
    ) {
      throw new Error(
        `Pre-warning period must be less than auto-expiry days (${value}).`,
      );
    }
    setCrossFieldError(null);
    if (onSaveAutoExpiry) {
      await onSaveAutoExpiry(value);
    }
  };

  const handleSavePreWarning = async (value: number | null) => {
    if (
      value !== null &&
      autoExpireValue !== null &&
      value >= autoExpireValue
    ) {
      const errMsg = `Pre-warning period must be less than auto-expiry days (${autoExpireValue}).`;
      setCrossFieldError(errMsg);
      throw new Error(errMsg);
    }
    setCrossFieldError(null);
    if (onSavePreWarning) {
      await onSavePreWarning(value);
    }
  };

  return (
    <section
      data-testid={testID ?? "calendar-auto-expiry-settings"}
      className="space-y-4 rounded-lg border border-neutral-200 bg-white"
    >
      <div className="px-4 pt-4">
        <h3 className="text-h3 font-medium text-neutral-900">
          Auto-Expiry Settings
        </h3>
        <p className="text-caption text-neutral-600">
          Conflicts that are not manually resolved will auto-resolve to
          Pilot&apos;s version.
        </p>
      </div>

      <div className="divide-y divide-neutral-200">
        <SettingControl
          settingKey={AUTO_EXPIRE_KEY}
          label="Auto-expiry period"
          description="Days before an unresolved conflict auto-resolves to Pilot's version."
          value={autoExpireValue}
          defaultValue={autoExpireDefault}
          scope={autoExpireScope}
          saveMode="blur"
          onSave={handleSaveAutoExpiry}
          onRevert={onRevertAutoExpiry}
          inputType="integer"
          validationRules={
            autoExpiryCatalogEntry?.validationRules ?? { min: 1, max: 365 }
          }
          unit="days"
          testID="auto-expire-days-input"
        />

        <SettingControl
          settingKey={PRE_WARNING_KEY}
          label="Pre-warning period"
          description="Days before expiry when the warning badge appears on pending conflicts."
          value={preWarningValue}
          defaultValue={preWarningDefault}
          scope={preWarningScope}
          saveMode="blur"
          onSave={handleSavePreWarning}
          onRevert={onRevertPreWarning}
          inputType="integer"
          validationRules={
            preWarningCatalogEntry?.validationRules ?? { min: 1, max: 30 }
          }
          unit="days before expiry"
          effectiveRangeLabel={
            autoExpireValue !== null && preWarningValue !== null
              ? `Effective: ${autoExpireValue} days · Pre-warning at: ${preWarningValue} days`
              : undefined
          }
          testID="pre-warning-days-input"
        />
      </div>

      {crossFieldError && (
        <div className="px-4 pb-4">
          <p role="alert" className="text-caption text-fault-600">
            {crossFieldError}
          </p>
        </div>
      )}
    </section>
  );
}
