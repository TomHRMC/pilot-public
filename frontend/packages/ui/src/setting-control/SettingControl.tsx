/**
 * SettingControl — FE-B11
 *
 * Location: packages/ui/src/setting-control/SettingControl.tsx
 *
 * Canonical setting field component for any tenant-level or user-level setting
 * following the system-default-with-tenant-override pattern (arch doc §16.5).
 *
 * Three visual states:
 *   State 1: scope='system' — inheriting default (muted annotation)
 *   State 2: scope='tenant'|'user' — actively overridden ("Revert to default" link)
 *   State revert-pending: inline confirmation visible
 *
 * Platform-aware: web uses Tailwind div+input; mobile uses Gluestack via Platform.OS.
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */

"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { Platform } from "react-native";
import type { SettingControlProps, SettingControlPhase } from "./types";
import { RevertToDefaultDialog } from "./RevertToDefaultDialog";

// ─── Platform-resolved primitives ────────────────────────────────────────────

const isWeb = Platform.OS === "web";

// ─── Helper ──────────────────────────────────────────────────────────────────

function formatDisplayValue(value: unknown, unit?: string): string {
  if (value === null || value === undefined) return "—";
  const str = String(value);
  return unit ? `${str} ${unit}` : str;
}

// ─── Web implementation ───────────────────────────────────────────────────────

function SettingControlWeb<T = unknown>({
  settingKey,
  label,
  description,
  value,
  defaultValue,
  scope,
  saveMode,
  onSave,
  onRevert,
  readOnly = false,
  inputType = "integer",
  validationRules,
  selectOptions,
  unit,
  effectiveRangeLabel,
  provenanceAnnotation,
  testID,
}: SettingControlProps<T>) {
  const [phase, setPhase] = useState<SettingControlPhase>({ phase: "clean" });
  const [draftValue, setDraftValue] = useState<T>(value);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isReverting, setIsReverting] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync draftValue when value prop changes (optimistic rollback)
  useEffect(() => {
    if (phase.phase === "clean" || phase.phase === "saved") {
      setDraftValue(value);
    }
  }, [value, phase.phase]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  const isState2 = scope === "tenant" || scope === "user";
  const isInheriting = scope === "system" || scope === "fallback";

  const validateValue = useCallback(
    (val: T): string | null => {
      if (!validationRules) return null;
      const num = Number(val);
      if (validationRules.min !== undefined && num < validationRules.min) {
        return `Must be at least ${validationRules.min}${unit ? ` ${unit}` : ""}.`;
      }
      if (validationRules.max !== undefined && num > validationRules.max) {
        return `Must be at most ${validationRules.max}${unit ? ` ${unit}` : ""}.`;
      }
      if (
        validationRules.allowedValues &&
        !validationRules.allowedValues.includes(String(val))
      ) {
        return `Must be one of: ${validationRules.allowedValues.join(", ")}.`;
      }
      return null;
    },
    [validationRules, unit],
  );

  const handleBlur = useCallback(async () => {
    if (readOnly || saveMode !== "blur") return;
    if (draftValue === value) return; // No change

    const error = validateValue(draftValue);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);

    const prevValue = value;
    setPhase({ phase: "save-pending", draftValue });

    try {
      await onSave(draftValue);
      setPhase({ phase: "saved", confirmedAt: Date.now() });
      savedTimerRef.current = setTimeout(() => {
        setPhase({ phase: "clean" });
      }, 2000);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Save failed. Try again.";
      setPhase({ phase: "error", error: msg, draftValue });
      setDraftValue(prevValue);
    }
  }, [readOnly, saveMode, draftValue, value, validateValue, onSave]);

  const handleChange = useCallback((newVal: T) => {
    setDraftValue(newVal);
    setPhase({ phase: "editing", draftValue: newVal });
    setValidationError(null);
  }, []);

  const handleToggleChange = useCallback(
    async (newVal: T) => {
      if (readOnly) return;
      setDraftValue(newVal);
      if (saveMode === "blur") {
        const prevValue = value;
        setPhase({ phase: "save-pending", draftValue: newVal });
        try {
          await onSave(newVal);
          setPhase({ phase: "saved", confirmedAt: Date.now() });
          savedTimerRef.current = setTimeout(() => {
            setPhase({ phase: "clean" });
          }, 2000);
        } catch (err) {
          const msg =
            err instanceof Error ? err.message : "Save failed. Try again.";
          setPhase({ phase: "error", error: msg, draftValue: newVal });
          setDraftValue(prevValue);
        }
      }
    },
    [readOnly, saveMode, value, onSave],
  );

  const handleRevertClick = () => {
    setPhase({ phase: "revert-pending" });
  };

  const handleRevertConfirm = async () => {
    if (!onRevert) return;
    setIsReverting(true);
    try {
      await onRevert();
      setPhase({ phase: "clean" });
      setDraftValue(defaultValue);
    } catch {
      // Revert failed — stay in revert-pending so user can retry
    } finally {
      setIsReverting(false);
    }
  };

  const handleRevertCancel = () => {
    setPhase({ phase: "clean" });
  };

  const isPending = phase.phase === "save-pending";
  const isSaved = phase.phase === "saved";
  const isError = phase.phase === "error";
  const isRevertPending = phase.phase === "revert-pending";
  const displayError = isError ? phase.error : (validationError ?? null);

  // ─── Read-only mode ────────────────────────────────────────────────────────
  if (readOnly) {
    const provText =
      provenanceAnnotation === "tenant"
        ? "Set by your tenant"
        : provenanceAnnotation === "system"
          ? "Default value"
          : isState2
            ? "Set by your tenant"
            : "Default value";

    return (
      <div
        data-testid={testID ?? `setting-control-${settingKey}`}
        className="space-y-1.5 p-4"
      >
        <p className="text-body font-medium text-neutral-900">{label}</p>
        {description && (
          <p className="text-caption text-neutral-600">{description}</p>
        )}
        <p className="text-body text-neutral-900">
          {formatDisplayValue(value, unit)}
        </p>
        <p
          className="text-caption text-neutral-500"
          data-testid={
            testID ? `${testID}-provenance` : `setting-provenance-${settingKey}`
          }
        >
          {provText}
        </p>
        {effectiveRangeLabel && (
          <p className="text-caption text-neutral-600">{effectiveRangeLabel}</p>
        )}
      </div>
    );
  }

  // ─── Input rendering ───────────────────────────────────────────────────────
  const renderInput = () => {
    const inputId = `setting-${settingKey}`;
    const isDisabled = isPending || isReverting;

    if (inputType === "boolean") {
      return (
        <button
          id={inputId}
          role="switch"
          type="button"
          aria-checked={Boolean(draftValue)}
          disabled={isDisabled}
          onClick={() => handleToggleChange(!draftValue as unknown as T)}
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
            draftValue ? "bg-brand-600" : "bg-neutral-200"
          }`}
          data-testid={
            testID ? `${testID}-toggle` : `setting-toggle-${settingKey}`
          }
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
              draftValue ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      );
    }

    if (inputType === "select" || inputType === "preset-select") {
      return (
        <select
          id={inputId}
          value={String(draftValue ?? "")}
          onChange={(e) => handleChange(e.target.value as unknown as T)}
          onBlur={handleBlur}
          disabled={isDisabled}
          className={`w-48 rounded-md border bg-white px-3 py-2 text-body text-neutral-900 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:opacity-60 ${
            displayError ? "border-fault-200" : "border-neutral-200"
          }`}
          data-testid={
            testID ? `${testID}-select` : `setting-select-${settingKey}`
          }
          aria-invalid={!!displayError}
          aria-describedby={displayError ? `${settingKey}-error` : undefined}
        >
          <option value="">Select…</option>
          {(selectOptions ?? []).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
              {opt.recommended ? " (recommended)" : ""}
            </option>
          ))}
        </select>
      );
    }

    // Default: integer or string text input
    return (
      <div className="flex items-center gap-2">
        <input
          id={inputId}
          type={inputType === "integer" ? "number" : "text"}
          value={
            draftValue === null || draftValue === undefined
              ? ""
              : String(draftValue)
          }
          onChange={(e) => {
            if (inputType === "integer") {
              const raw = e.target.value;
              if (raw === "") {
                handleChange(null as unknown as T);
              } else {
                const num = parseInt(raw, 10);
                if (!isNaN(num)) handleChange(num as unknown as T);
              }
            } else {
              handleChange(e.target.value as unknown as T);
            }
          }}
          onBlur={handleBlur}
          disabled={isDisabled}
          min={validationRules?.min}
          max={validationRules?.max}
          className={`w-24 rounded-md border bg-white px-3 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:opacity-60 ${
            displayError ? "border-fault-200" : "border-neutral-200"
          }`}
          data-testid={
            testID ? `${testID}-input` : `setting-input-${settingKey}`
          }
          aria-invalid={!!displayError}
          aria-describedby={displayError ? `${settingKey}-error` : undefined}
        />
        {unit && <span className="text-body text-neutral-600">{unit}</span>}
      </div>
    );
  };

  return (
    <div
      data-testid={testID ?? `setting-control-${settingKey}`}
      className="space-y-1.5 p-4"
    >
      {/* Label row */}
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor={`setting-${settingKey}`}
          className="text-body font-medium text-neutral-900"
        >
          {label}
        </label>

        {/* Status indicators */}
        <div className="flex items-center gap-2">
          {isPending && (
            <span
              className="text-neutral-400"
              aria-label="Saving…"
              data-testid={
                testID ? `${testID}-pending` : `setting-pending-${settingKey}`
              }
            >
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
            </span>
          )}
          {isSaved && (
            <span
              className="text-margin-600 text-caption"
              aria-label="Saved"
              data-testid={
                testID ? `${testID}-saved` : `setting-saved-${settingKey}`
              }
            >
              ✓ Saved
            </span>
          )}
        </div>
      </div>

      {description && (
        <p className="text-caption text-neutral-600">{description}</p>
      )}

      {/* Input */}
      {renderInput()}

      {/* Validation / save error */}
      {displayError && (
        <p
          id={`${settingKey}-error`}
          role="alert"
          className="text-caption text-fault-600"
          data-testid={
            testID ? `${testID}-error` : `setting-error-${settingKey}`
          }
        >
          {displayError}
        </p>
      )}

      {/* State 1 annotation */}
      {isInheriting && !displayError && (
        <p
          className="text-caption text-neutral-400"
          data-testid={
            testID
              ? `${testID}-default-annotation`
              : `setting-default-${settingKey}`
          }
        >
          Default · {formatDisplayValue(defaultValue, unit)}
        </p>
      )}

      {/* State 2: tenant override pill + revert link */}
      {isState2 && !displayError && !isRevertPending && (
        <div className="flex items-center gap-2">
          <span className="rounded px-2 py-0.5 text-caption font-medium bg-brand-100 text-brand-700">
            tenant override
          </span>
          {onRevert && (
            <button
              type="button"
              onClick={handleRevertClick}
              className="text-caption text-brand-600 hover:text-brand-800 focus:outline-none focus:underline"
              data-testid={
                testID
                  ? `${testID}-revert-link`
                  : `setting-revert-link-${settingKey}`
              }
            >
              Revert to default
            </button>
          )}
        </div>
      )}

      {/* Revert-pending inline confirmation */}
      {isRevertPending && (
        <RevertToDefaultDialog
          settingLabel={label}
          currentValue={value}
          defaultValue={defaultValue}
          unit={unit}
          onConfirm={handleRevertConfirm}
          onCancel={handleRevertCancel}
          isReverting={isReverting}
          testID={
            testID
              ? `${testID}-revert-dialog`
              : `setting-revert-dialog-${settingKey}`
          }
        />
      )}

      {/* Effective range helper */}
      {effectiveRangeLabel && (
        <p className="text-caption text-neutral-600">{effectiveRangeLabel}</p>
      )}
    </div>
  );
}

// ─── Mobile implementation ────────────────────────────────────────────────────

function SettingControlMobile<T = unknown>(props: SettingControlProps<T>) {
  // Import Gluestack lazily to avoid SSR issues
  // On mobile (React Native), we use VStack/Text/Pressable from Gluestack
  // For now, render a React Native-compatible structure using View/Text
  // The full Gluestack implementation follows the same logic as web
  const {
    settingKey,
    label,
    description,
    value,
    scope,
    readOnly = false,
    unit,
    effectiveRangeLabel,
    provenanceAnnotation,
    testID,
  } = props;

  // Determine provenance annotation
  const isState2 = scope === "tenant" || scope === "user";
  const provText =
    provenanceAnnotation === "tenant"
      ? "Set by your tenant"
      : provenanceAnnotation === "system"
        ? "Default value"
        : isState2
          ? "Set by your tenant"
          : "Default value";

  // Mobile always renders read-only provenance annotation (per Decision 5)
  // Editable mobile controls use EffectiveSettingDisplay for per-user overrides
  return (
    <div
      data-testid={testID ?? `setting-control-mobile-${settingKey}`}
      className="flex flex-col gap-1.5 p-4"
    >
      <span className="font-medium text-neutral-900">{label}</span>
      {description && (
        <span className="text-caption text-neutral-600">{description}</span>
      )}
      <span className="text-neutral-900">
        {formatDisplayValue(value, unit)}
      </span>
      {readOnly && (
        <span
          className="text-caption text-neutral-500"
          data-testid={
            testID ? `${testID}-provenance` : `setting-provenance-${settingKey}`
          }
        >
          {provText}
        </span>
      )}
      {effectiveRangeLabel && (
        <span className="text-caption text-neutral-600">
          {effectiveRangeLabel}
        </span>
      )}
    </div>
  );
}

// ─── Platform-resolved export ─────────────────────────────────────────────────

export function SettingControl<T = unknown>(props: SettingControlProps<T>) {
  if (isWeb) {
    return <SettingControlWeb {...props} />;
  }
  return <SettingControlMobile {...props} />;
}
