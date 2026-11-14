"use client";

/**
 * DefaultsAnnotatedField — C-B16 §16.5 visual-language wrapper
 *
 * Location: apps/web/src/features/tenant-site/components/DefaultsAnnotatedField.tsx
 *
 * Composes the SettingControl visual contract (State 1 default-source annotation,
 * State 2 override pill) without using the locked SettingControl save machinery.
 * The hosted-site form saves as a batch PUT — SettingControl's blur-save/group-save
 * semantics don't fit.
 *
 * web spec §7.3:
 *   State 1 (inheriting): "Default from 10DLC profile: {value}" annotation
 *   State 2 (overridden): "overridden" pill + "Revert to profile default" link
 *   State 3 (no default): no annotation
 *
 * WCAG 2.5.8: revert link uses inline-block py-1 for ≥24px tap target.
 */

import React from "react";

interface DefaultsAnnotatedFieldProps {
  label: string;
  required?: boolean;
  /** The current field value */
  value: string;
  /** The default value from the 10DLC profile (null = no default → State 3) */
  defaultValue: string | null;
  /** Source label, e.g. "10DLC profile" */
  defaultSourceLabel?: string;
  helperText?: string;
  errorText?: string;
  inputId: string;
  /** Render the input element — receives value + onChange */
  children: React.ReactNode;
  /** Called when "Revert to profile default" is clicked */
  onRevert?: () => void;
  /** Whether the field is disabled (e.g. slug locked after publish) */
  disabled?: boolean;
}

export function DefaultsAnnotatedField({
  label,
  required = false,
  value,
  defaultValue,
  defaultSourceLabel = "10DLC profile",
  helperText,
  errorText,
  inputId,
  children,
  onRevert,
  disabled = false,
}: DefaultsAnnotatedFieldProps) {
  const hasDefault = defaultValue !== null && defaultValue !== undefined;
  const isOverridden = hasDefault && value !== defaultValue;
  const isInheriting = hasDefault && value === defaultValue;

  const helperId = `${inputId}-helper`;
  const errorId = `${inputId}-error`;
  const annotationId = `${inputId}-annotation`;

  return (
    <div>
      <label
        htmlFor={inputId}
        className="mb-1 text-sm font-medium text-neutral-700"
      >
        {label}
        {required && <span className="text-alert-600">*</span>}
      </label>

      {children}

      {/* State 1 — Inheriting default */}
      {isInheriting && !disabled && (
        <p id={annotationId} className="mt-1 text-caption text-neutral-400">
          Default from {defaultSourceLabel}: {defaultValue}
        </p>
      )}

      {/* State 2 — Overridden */}
      {isOverridden && hasDefault && !disabled && onRevert && (
        <div className="mt-1 flex items-center gap-2">
          <span className="rounded bg-brand-100 px-2 py-0.5 text-caption font-medium text-brand-700">
            overridden
          </span>
          <button
            type="button"
            onClick={onRevert}
            className="inline-block py-1 text-caption text-brand-600 hover:text-brand-800 focus:outline-none focus:underline focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2"
          >
            Revert to profile default
          </button>
        </div>
      )}

      {/* Helper text */}
      {helperText && !errorText && (
        <p id={helperId} className="mt-1 text-xs text-neutral-500">
          {helperText}
        </p>
      )}

      {/* Error text */}
      {errorText && (
        <p id={errorId} role="alert" className="mt-1 text-xs text-fault-600">
          {errorText}
        </p>
      )}
    </div>
  );
}
