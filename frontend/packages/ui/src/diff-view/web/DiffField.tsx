/**
 * DiffField — single field diff row (web)
 *
 * Location: packages/ui/src/diff-view/web/DiffField.tsx
 * Internal component — not exported from barrel.
 *
 * Renders amber (modified), green (added), red (removed), neutral (unchanged).
 * Colors come from token classes: alert / margin / fault / neutral ramps.
 * NO hardcoded hex values or pixel sizes.
 */

import React from "react";
import type { DiffField as DiffFieldType } from "../types";
import { deriveChangeType, fieldNameToLabel } from "../utils";

interface DiffFieldProps {
  field: DiffFieldType;
  onRevert?: (pendingEditId: string) => void;
  showSideLabels?: boolean;
  baseLabel?: string;
  modifiedLabel?: string;
}

export function DiffField({
  field,
  onRevert,
  showSideLabels = false,
  baseLabel = "Before",
  modifiedLabel = "After",
}: DiffFieldProps) {
  const changeType =
    field.changeType ?? deriveChangeType(field.baseValue, field.modifiedValue);

  const label = field.label ?? fieldNameToLabel(field.fieldName);

  if (changeType === "unchanged") {
    return null; // Unchanged fields are not rendered (clutter reduction)
  }

  // Map change type to token-based Tailwind classes (NO hex values)
  const containerClass = {
    modified: "bg-alert-50 border-l-2 border-alert-400",
    added: "bg-margin-50 border-l-2 border-margin-400",
    removed: "bg-fault-50 border-l-2 border-fault-400",
  }[changeType];

  const labelClass = {
    modified: "text-alert-800",
    added: "text-margin-800",
    removed: "text-fault-800",
  }[changeType];

  const changeBadgeClass = {
    modified: "bg-alert-100 text-alert-800",
    added: "bg-margin-100 text-margin-800",
    removed: "bg-fault-100 text-fault-800",
  }[changeType];

  const changeBadgeLabel = {
    modified: "Modified",
    added: "Added",
    removed: "Removed",
  }[changeType];

  const formatDisplayValue = (val: DiffFieldType["baseValue"]) => {
    if (val === null || val === undefined)
      return <em className="text-neutral-400">—</em>;
    if (typeof val === "boolean") return val ? "Yes" : "No";
    return String(val);
  };

  return (
    <div
      className={`px-3 py-2 rounded-sm mb-1 ${containerClass}`}
      role="listitem"
      aria-label={`${label}: ${changeBadgeLabel}`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className={`text-caption font-medium ${labelClass}`}>
          {label}
        </span>
        <span
          className={`text-caption px-1.5 py-0.5 rounded-sm font-medium ${changeBadgeClass}`}
          aria-label={`Change type: ${changeBadgeLabel}`}
        >
          {changeBadgeLabel}
        </span>
      </div>

      {changeType === "modified" && (
        <div className="flex items-start gap-2 text-body">
          <div className="flex-1">
            {showSideLabels && (
              <span className="text-caption text-neutral-400 block mb-0.5">
                {baseLabel}
              </span>
            )}
            <span className="line-through text-neutral-400">
              {formatDisplayValue(field.baseValue)}
            </span>
          </div>
          <span className="text-neutral-400 mt-0.5" aria-hidden="true">
            →
          </span>
          <div className="flex-1">
            {showSideLabels && (
              <span className="text-caption text-neutral-400 block mb-0.5">
                {modifiedLabel}
              </span>
            )}
            <span className="text-neutral-900 font-medium">
              {formatDisplayValue(field.modifiedValue)}
            </span>
          </div>
        </div>
      )}

      {changeType === "added" && (
        <div className="text-body">
          {showSideLabels && (
            <span className="text-caption text-neutral-400 block mb-0.5">
              {modifiedLabel}
            </span>
          )}
          <span className="text-margin-800 font-medium">
            {formatDisplayValue(field.modifiedValue)}
          </span>
        </div>
      )}

      {changeType === "removed" && (
        <div className="text-body">
          {showSideLabels && (
            <span className="text-caption text-neutral-400 block mb-0.5">
              {baseLabel}
            </span>
          )}
          <span className="line-through text-fault-800">
            {formatDisplayValue(field.baseValue)}
          </span>
        </div>
      )}

      {field.annotation && (
        <p className="text-caption text-neutral-600 mt-1 italic">
          {field.annotation}
        </p>
      )}

      {onRevert && field.pendingEditId && (
        <button
          type="button"
          className="text-caption text-brand-600 hover:text-brand-800 mt-1 underline"
          onClick={() => onRevert(field.pendingEditId!)}
          aria-label={`Revert change to ${label}`}
        >
          Revert this change
        </button>
      )}
    </div>
  );
}
