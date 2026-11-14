/**
 * DiffLineItem — single quote line with diffs (web)
 *
 * Location: packages/ui/src/diff-view/web/DiffLineItem.tsx
 * Internal component — not exported from barrel.
 */

import React from "react";
import type { DiffLineItem as DiffLineItemType } from "../types";
import { DiffField } from "./DiffField";

interface DiffLineItemProps {
  lineItem: DiffLineItemType;
  onRevertField?: (pendingEditId: string) => void;
}

export function DiffLineItemRow({
  lineItem,
  onRevertField,
}: DiffLineItemProps) {
  const lineContainerClass = {
    added: "bg-margin-50 border border-margin-400",
    removed: "bg-fault-50 border border-fault-400 opacity-75",
    modified: "bg-alert-50 border border-alert-400",
    unchanged: "bg-neutral-50 border border-neutral-200",
  }[lineItem.lineChangeType];

  const lineBadgeClass = {
    added: "bg-margin-100 text-margin-800",
    removed: "bg-fault-100 text-fault-800",
    modified: "bg-alert-100 text-alert-800",
    unchanged: "bg-neutral-100 text-neutral-600",
  }[lineItem.lineChangeType];

  const lineBadgeLabel = {
    added: "Added",
    removed: "Removed",
    modified: "Modified",
    unchanged: "Unchanged",
  }[lineItem.lineChangeType];

  if (lineItem.lineChangeType === "unchanged") return null;

  return (
    <div
      className={`rounded-md p-3 mb-2 ${lineContainerClass}`}
      role="listitem"
      aria-label={`Line item: ${lineItem.label}, ${lineBadgeLabel}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-body font-medium text-neutral-900">
            {lineItem.label}
          </span>
          {!lineItem.customerVisible && (
            <span className="text-caption text-neutral-400 italic">
              (internal)
            </span>
          )}
        </div>
        <span
          className={`text-caption px-1.5 py-0.5 rounded-sm font-medium ${lineBadgeClass}`}
          aria-label={`Change type: ${lineBadgeLabel}`}
        >
          {lineBadgeLabel}
        </span>
      </div>

      {lineItem.fields.length > 0 && (
        <div role="list" aria-label={`Field changes for ${lineItem.label}`}>
          {lineItem.fields.map((field) => (
            <DiffField
              key={field.fieldName}
              field={field}
              onRevert={onRevertField}
            />
          ))}
        </div>
      )}
    </div>
  );
}
