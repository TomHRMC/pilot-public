/**
 * ConflictTypeLabel — pill label for conflict type
 *
 * Location: packages/ui/src/integration-conflict-resolver/ConflictTypeLabel.tsx
 *
 * Renders a colored pill for each of the three bilateral conflict types:
 * - modified_modified → "Modified ↔ Modified" (amber)
 * - deleted_modified  → "Deleted ↔ Modified"  (red)
 * - modified_deleted  → "Modified ↔ Deleted"  (red)
 *
 * All tokens from pilotPreset; zero hardcoded colors.
 */

import React from "react";
import type { ConflictTypeLabelProps, ConflictType } from "./types";

const CONFLICT_TYPE_CONFIG: Record<
  ConflictType,
  { label: string; className: string }
> = {
  modified_modified: {
    label: "Modified ↔ Modified",
    className: "bg-alert-100 text-alert-700 border border-alert-200",
  },
  deleted_modified: {
    label: "Deleted ↔ Modified",
    className: "bg-fault-100 text-fault-700 border border-fault-200",
  },
  modified_deleted: {
    label: "Modified ↔ Deleted",
    className: "bg-fault-100 text-fault-700 border border-fault-200",
  },
};

export function ConflictTypeLabel({
  conflictType,
  testID,
}: ConflictTypeLabelProps) {
  const config = CONFLICT_TYPE_CONFIG[conflictType];

  if (!config) return null;

  return (
    <span
      data-testid={testID ?? "conflict-type-label"}
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-caption font-medium whitespace-nowrap ${config.className}`}
    >
      {config.label}
    </span>
  );
}
