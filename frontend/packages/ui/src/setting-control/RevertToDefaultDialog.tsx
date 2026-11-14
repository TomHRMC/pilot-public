/**
 * RevertToDefaultDialog — FE-B11
 *
 * Location: packages/ui/src/setting-control/RevertToDefaultDialog.tsx
 *
 * Inline confirmation component rendered inside SettingControl when the owner
 * clicks "Revert to default". Decision 6: renders inline (not floating modal).
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */

"use client";

import React from "react";
import type { RevertToDefaultDialogProps } from "./types";

export function RevertToDefaultDialog({
  settingLabel,
  currentValue,
  defaultValue,
  unit,
  onConfirm,
  onCancel,
  isReverting,
  testID,
}: RevertToDefaultDialogProps) {
  const formatValue = (v: unknown): string => {
    if (v === null || v === undefined) return "—";
    return String(v);
  };

  const suffix = unit ? ` ${unit}` : "";

  return (
    <div
      className="mt-2 rounded-md border border-neutral-200 bg-neutral-50 p-3"
      role="region"
      aria-label={`Revert ${settingLabel} to default`}
      data-testid={
        testID ??
        `${settingLabel.replace(/\s+/g, "-").toLowerCase()}-revert-dialog`
      }
    >
      <p className="text-caption text-neutral-900">
        Revert <span className="font-medium">&ldquo;{settingLabel}&rdquo;</span>{" "}
        from{" "}
        <span className="font-medium">
          {formatValue(currentValue)}
          {suffix}
        </span>{" "}
        &rarr;{" "}
        <span className="font-medium">
          {formatValue(defaultValue)}
          {suffix}
        </span>{" "}
        <span className="text-neutral-600">(system default)</span>?
      </p>

      <div className="mt-2 flex items-center gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isReverting}
          className="rounded-md border border-neutral-200 px-3 py-1 text-caption text-neutral-700 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-neutral-200 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid={testID ? `${testID}-cancel` : "revert-dialog-cancel"}
        >
          Cancel
        </button>

        <button
          type="button"
          onClick={onConfirm}
          disabled={isReverting}
          aria-busy={isReverting}
          className="flex items-center gap-1.5 rounded-md bg-brand-600 px-3 py-1 text-caption font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid={testID ? `${testID}-confirm` : "revert-dialog-confirm"}
        >
          {isReverting ? (
            <>
              <span
                className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent"
                aria-hidden="true"
              />
              Reverting…
            </>
          ) : (
            "Revert"
          )}
        </button>
      </div>
    </div>
  );
}
