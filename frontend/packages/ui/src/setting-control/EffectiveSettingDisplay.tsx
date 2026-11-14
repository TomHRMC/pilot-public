/**
 * EffectiveSettingDisplay — FE-B11
 *
 * Location: packages/ui/src/setting-control/EffectiveSettingDisplay.tsx
 *
 * Renders the three-tier resolution chain (user → tenant → system) for settings
 * that allow per-user override (arch doc §16.5 Mockup C).
 *
 * Web mode: owner sees all three tiers + per_user_override_allowed meta-toggle.
 * Mobile mode: tech sees their own override + tenant default + "Match tenant" link.
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */

"use client";

import React, { useState } from "react";
import { Platform } from "react-native";
import type { EffectiveSettingDisplayProps } from "./types";

const isWeb = Platform.OS === "web";

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "On" : "Off";
  return String(value);
}

// ─── Tier badge ───────────────────────────────────────────────────────────────

function TierBadge({
  tier,
  isActive,
}: {
  tier: "User" | "Tenant" | "System";
  isActive: boolean;
}) {
  return (
    <span
      className={`rounded px-2 py-0.5 text-caption font-medium ${
        isActive
          ? "bg-brand-100 text-brand-700"
          : "bg-neutral-100 text-neutral-600"
      }`}
    >
      {tier}
    </span>
  );
}

// ─── Web implementation ───────────────────────────────────────────────────────

function EffectiveSettingDisplayWeb({
  settingKey,
  label,
  description,
  tiers,
  activeTier,
  userCanEdit,
  allowsUserOverride,
  onSaveUserOverride,
  onRevertUserOverride,
  inputType = "boolean",
  selectOptions,
  testID,
}: EffectiveSettingDisplayProps) {
  const [draftUserValue, setDraftUserValue] = useState<unknown>(
    tiers.user.value,
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const isUserActive = activeTier === "user";
  const isTenantActive = activeTier === "tenant";
  const isSystemActive = activeTier === "system" || activeTier === "fallback";

  const handleSaveUserOverride = async () => {
    if (!onSaveUserOverride) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await onSaveUserOverride(draftUserValue);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleUserOverride = async (val: unknown) => {
    if (!onSaveUserOverride) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await onSaveUserOverride(val);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      data-testid={testID ?? `effective-setting-${settingKey}`}
      className="space-y-1.5 p-4"
    >
      <p className="text-body font-medium text-neutral-900">{label}</p>
      {description && (
        <p className="text-caption text-neutral-600">{description}</p>
      )}

      <div className="mt-2 space-y-2 rounded-md border border-neutral-200 bg-neutral-50 p-3">
        {/* User tier */}
        <div
          className={`flex items-center justify-between gap-2 rounded-sm px-2 py-1.5 ${
            isUserActive ? "bg-white shadow-sm" : ""
          }`}
          data-testid={
            testID
              ? `${testID}-user-row`
              : `effective-setting-user-row-${settingKey}`
          }
        >
          <div className="flex items-center gap-2">
            <TierBadge tier="User" isActive={isUserActive} />
            {tiers.user.exists ? (
              <span className="text-body text-neutral-900">
                {formatValue(tiers.user.value)}
              </span>
            ) : (
              <span className="text-caption text-neutral-400">
                {allowsUserOverride
                  ? "Using tenant default"
                  : "Set by your tenant"}
              </span>
            )}
          </div>

          {userCanEdit && allowsUserOverride && (
            <div className="flex items-center gap-1.5">
              {inputType === "boolean" ? (
                <button
                  role="switch"
                  type="button"
                  aria-checked={Boolean(
                    tiers.user.exists ? tiers.user.value : tiers.tenant.value,
                  )}
                  disabled={isSaving}
                  onClick={() =>
                    handleToggleUserOverride(
                      !(tiers.user.exists
                        ? tiers.user.value
                        : tiers.tenant.value),
                    )
                  }
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1 disabled:opacity-50 ${
                    (tiers.user.exists ? tiers.user.value : tiers.tenant.value)
                      ? "bg-brand-600"
                      : "bg-neutral-200"
                  }`}
                  data-testid={
                    testID
                      ? `${testID}-user-toggle`
                      : `effective-setting-user-toggle-${settingKey}`
                  }
                >
                  <span
                    className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                      (
                        tiers.user.exists
                          ? tiers.user.value
                          : tiers.tenant.value
                      )
                        ? "translate-x-6"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              ) : inputType === "select" ? (
                <select
                  value={String(draftUserValue ?? "")}
                  onChange={(e) => setDraftUserValue(e.target.value)}
                  onBlur={handleSaveUserOverride}
                  disabled={isSaving}
                  className="rounded-md border border-neutral-200 bg-white px-2 py-1 text-caption text-neutral-900 focus:outline-none focus:ring-1 focus:ring-brand-600"
                  data-testid={
                    testID
                      ? `${testID}-user-select`
                      : `effective-setting-user-select-${settingKey}`
                  }
                >
                  {(selectOptions ?? []).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              ) : null}

              {tiers.user.exists && onRevertUserOverride && (
                <button
                  type="button"
                  onClick={onRevertUserOverride}
                  disabled={isSaving}
                  className="text-caption text-brand-600 hover:text-brand-800 focus:outline-none focus:underline disabled:opacity-50"
                  data-testid={
                    testID
                      ? `${testID}-user-revert`
                      : `effective-setting-user-revert-${settingKey}`
                  }
                >
                  Match tenant
                </button>
              )}
            </div>
          )}

          {!allowsUserOverride && (
            <span className="text-caption text-neutral-500">
              Set by your tenant
            </span>
          )}
        </div>

        {saveError && (
          <p role="alert" className="text-caption text-fault-600">
            {saveError}
          </p>
        )}

        {/* Tenant tier */}
        <div
          className={`flex items-center gap-2 rounded-sm px-2 py-1.5 ${
            isTenantActive ? "bg-white shadow-sm" : ""
          }`}
          data-testid={
            testID
              ? `${testID}-tenant-row`
              : `effective-setting-tenant-row-${settingKey}`
          }
        >
          <TierBadge tier="Tenant" isActive={isTenantActive} />
          {tiers.tenant.exists ? (
            <span className="text-body text-neutral-900">
              {formatValue(tiers.tenant.value)}
            </span>
          ) : (
            <span className="text-caption text-neutral-400">
              Using system default
            </span>
          )}
        </div>

        {/* System tier */}
        <div
          className={`flex items-center gap-2 rounded-sm px-2 py-1.5 ${
            isSystemActive ? "bg-white shadow-sm" : ""
          }`}
          data-testid={
            testID
              ? `${testID}-system-row`
              : `effective-setting-system-row-${settingKey}`
          }
        >
          <TierBadge tier="System" isActive={isSystemActive} />
          <span className="text-body text-neutral-900">
            {formatValue(tiers.system.value)}
          </span>
          <span className="text-caption text-neutral-400">(default)</span>
        </div>
      </div>
    </div>
  );
}

// ─── Mobile implementation ────────────────────────────────────────────────────

function EffectiveSettingDisplayMobile({
  settingKey,
  label,
  description,
  tiers,
  activeTier,
  userCanEdit,
  allowsUserOverride,
  onSaveUserOverride,
  onRevertUserOverride,
  inputType = "boolean",
  testID,
}: EffectiveSettingDisplayProps) {
  const [isSaving, setIsSaving] = useState(false);

  const userDisplayValue = tiers.user.exists
    ? tiers.user.value
    : tiers.tenant.exists
      ? tiers.tenant.value
      : tiers.system.value;

  const tenantDisplayValue = tiers.tenant.exists
    ? tiers.tenant.value
    : tiers.system.value;

  const handleToggle = async (val: unknown) => {
    if (!onSaveUserOverride) return;
    setIsSaving(true);
    try {
      await onSaveUserOverride(val);
    } finally {
      setIsSaving(false);
    }
  };

  // Hide system tier when same as tenant (mobile simplification per Decision 5)
  const showSystemTier =
    !tiers.tenant.exists ||
    String(tiers.system.value) !== String(tiers.tenant.value);

  return (
    <div
      data-testid={testID ?? `effective-setting-mobile-${settingKey}`}
      className="flex flex-col gap-1.5 p-4"
    >
      <span className="font-medium text-neutral-900">{label}</span>
      {description && (
        <span className="text-caption text-neutral-600">{description}</span>
      )}

      {/* User tier row */}
      <div
        className="flex items-center gap-2"
        data-testid={
          testID
            ? `${testID}-mobile-user-row`
            : `effective-setting-mobile-user-${settingKey}`
        }
      >
        <span
          className={`rounded px-2 py-0.5 text-caption font-medium ${
            activeTier === "user"
              ? "bg-brand-100 text-brand-700"
              : "bg-neutral-100 text-neutral-600"
          }`}
        >
          You
        </span>
        <span className="text-neutral-900">
          {formatValue(userDisplayValue)}
        </span>
        {userCanEdit && allowsUserOverride && inputType === "boolean" && (
          <button
            role="switch"
            type="button"
            aria-checked={Boolean(userDisplayValue)}
            disabled={isSaving}
            onClick={() => handleToggle(!userDisplayValue)}
            className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1 disabled:opacity-50 ${
              userDisplayValue ? "bg-brand-600" : "bg-neutral-200"
            }`}
            data-testid={
              testID
                ? `${testID}-mobile-toggle`
                : `effective-setting-mobile-toggle-${settingKey}`
            }
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                userDisplayValue ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        )}
        {tiers.user.exists && onRevertUserOverride && (
          <button
            type="button"
            onClick={onRevertUserOverride}
            className="text-caption text-brand-600 hover:text-brand-800 focus:outline-none focus:underline disabled:opacity-50"
            data-testid={
              testID
                ? `${testID}-mobile-match-tenant`
                : `effective-setting-mobile-match-${settingKey}`
            }
          >
            Match tenant default
          </button>
        )}
      </div>

      {/* Tenant tier row */}
      <div className="flex items-center gap-2">
        <span
          className={`rounded px-2 py-0.5 text-caption font-medium ${
            activeTier === "tenant"
              ? "bg-brand-100 text-brand-700"
              : "bg-neutral-100 text-neutral-600"
          }`}
        >
          Tenant
        </span>
        <span className="text-neutral-900">
          {formatValue(tenantDisplayValue)}
        </span>
        <span className="text-caption text-neutral-500">
          {tiers.tenant.exists ? "tenant default" : "system default"}
        </span>
      </div>

      {/* System tier (only when distinct from tenant) */}
      {showSystemTier && (
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-2 py-0.5 text-caption font-medium ${
              activeTier === "system" || activeTier === "fallback"
                ? "bg-brand-100 text-brand-700"
                : "bg-neutral-100 text-neutral-600"
            }`}
          >
            System
          </span>
          <span className="text-neutral-500">
            {formatValue(tiers.system.value)}
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Platform-resolved export ─────────────────────────────────────────────────

export function EffectiveSettingDisplay(props: EffectiveSettingDisplayProps) {
  const mode = props.displayMode ?? (isWeb ? "web" : "mobile");
  if (mode === "web") {
    return <EffectiveSettingDisplayWeb {...props} />;
  }
  return <EffectiveSettingDisplayMobile {...props} />;
}
