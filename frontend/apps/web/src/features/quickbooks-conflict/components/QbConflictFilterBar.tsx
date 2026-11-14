/**
 * QbConflictFilterBar — filter chips for QB conflicts queue
 *
 * Location: apps/web/src/features/quickbooks-conflict/components/QbConflictFilterBar.tsx
 *
 * Established FE-B9. Entity-type multi-select pills + master-direction filter.
 */

"use client";

import React from "react";
import type { QbEntityType } from "../types";

interface QbConflictFilterBarProps {
  entityType: QbEntityType | undefined;
  onEntityTypeChange: (type: QbEntityType | undefined) => void;
  masterFilter: "pilot" | "external" | undefined;
  onMasterFilterChange: (filter: "pilot" | "external" | undefined) => void;
  counts?: Partial<Record<QbEntityType, number>>;
  testID?: string;
}

const ENTITY_TYPES: Array<{ value: QbEntityType; label: string }> = [
  { value: "invoice", label: "Invoice" },
  { value: "quote", label: "Quote" },
  { value: "customer", label: "Customer" },
  { value: "expense", label: "Expense" },
];

const MASTER_FILTERS: Array<{
  value: "pilot" | "external" | undefined;
  label: string;
}> = [
  { value: undefined, label: "All" },
  { value: "pilot", label: "Pilot is master" },
  { value: "external", label: "QB is master" },
];

export function QbConflictFilterBar({
  entityType,
  onEntityTypeChange,
  masterFilter,
  onMasterFilterChange,
  counts,
  testID,
}: QbConflictFilterBarProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid={testID ?? "qb-conflict-filter-bar"}
    >
      {/* Entity type pills */}
      <div
        className="flex items-center gap-1"
        role="group"
        aria-label="Entity type filter"
      >
        <button
          type="button"
          onClick={() => onEntityTypeChange(undefined)}
          className={`rounded-full px-3 py-1 text-caption font-medium transition-colors ${
            entityType === undefined
              ? "bg-brand-600 text-white"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
          aria-pressed={entityType === undefined}
          data-testid="entity-type-all"
        >
          All
        </button>
        {ENTITY_TYPES.map((t) => {
          const count = counts?.[t.value];
          return (
            <button
              key={t.value}
              type="button"
              onClick={() =>
                onEntityTypeChange(entityType === t.value ? undefined : t.value)
              }
              className={`rounded-full px-3 py-1 text-caption font-medium transition-colors ${
                entityType === t.value
                  ? "bg-brand-600 text-white"
                  : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
              }`}
              aria-pressed={entityType === t.value}
              data-testid={`entity-type-${t.value}`}
            >
              {t.label}
              {count !== undefined && (
                <span className="ml-1 opacity-75">({count})</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Separator */}
      <span className="text-neutral-300" aria-hidden="true">
        |
      </span>

      {/* Master direction filter */}
      <div
        className="flex items-center gap-1"
        role="group"
        aria-label="Master direction filter"
      >
        {MASTER_FILTERS.map((f) => (
          <button
            key={String(f.value)}
            type="button"
            onClick={() => onMasterFilterChange(f.value)}
            className={`rounded-full px-3 py-1 text-caption font-medium transition-colors ${
              masterFilter === f.value
                ? "bg-neutral-700 text-white"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
            }`}
            aria-pressed={masterFilter === f.value}
            data-testid={`master-filter-${f.value ?? "all"}`}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}
