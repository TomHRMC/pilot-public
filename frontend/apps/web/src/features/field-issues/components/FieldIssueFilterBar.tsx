/**
 * FieldIssueFilterBar — filter chips for field issues queue
 *
 * Location: apps/web/src/features/field-issues/components/FieldIssueFilterBar.tsx
 *
 * Established FE-B9. Active techs toggle (on by default), operation-type multi-select,
 * auto-recovered toggle.
 */

"use client";

import React from "react";
import type { FieldIssueOperationType, FieldIssueStatus } from "../types";

interface FieldIssueFilterBarProps {
  status: FieldIssueStatus | "all";
  onStatusChange: (status: FieldIssueStatus | "all") => void;
  operationType: FieldIssueOperationType | undefined;
  onOperationTypeChange: (type: FieldIssueOperationType | undefined) => void;
  activeTechsOnly: boolean;
  onActiveTechsOnlyChange: (value: boolean) => void;
  testID?: string;
}

const OPERATION_TYPES: Array<{
  value: FieldIssueOperationType;
  label: string;
}> = [
  { value: "time_entry", label: "Time entry" },
  { value: "expense", label: "Expense" },
  { value: "photo", label: "Photo" },
  { value: "status_change", label: "Status change" },
  { value: "loto", label: "LOTO" },
];

const STATUS_FILTERS: Array<{
  value: FieldIssueStatus | "all";
  label: string;
}> = [
  { value: "pending", label: "Pending" },
  { value: "auto_recovered", label: "Auto-recovered" },
  { value: "stale", label: "Stale" },
  { value: "all", label: "All" },
];

export function FieldIssueFilterBar({
  status,
  onStatusChange,
  operationType,
  onOperationTypeChange,
  activeTechsOnly,
  onActiveTechsOnlyChange,
  testID,
}: FieldIssueFilterBarProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid={testID ?? "field-issue-filter-bar"}
    >
      {/* Status filter chips */}
      <div
        className="flex items-center gap-1"
        role="group"
        aria-label="Status filter"
      >
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => onStatusChange(f.value)}
            className={`rounded-full px-3 py-1 text-caption font-medium transition-colors ${
              status === f.value
                ? "bg-brand-600 text-white"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
            }`}
            aria-pressed={status === f.value}
            data-testid={`status-filter-${f.value}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Separator */}
      <span className="text-neutral-300" aria-hidden="true">
        |
      </span>

      {/* Operation type multi-select */}
      <div
        className="flex items-center gap-1"
        role="group"
        aria-label="Operation type filter"
      >
        <span className="text-caption text-neutral-500">Type:</span>
        <button
          type="button"
          onClick={() => onOperationTypeChange(undefined)}
          className={`rounded-full px-3 py-1 text-caption font-medium transition-colors ${
            operationType === undefined
              ? "bg-neutral-700 text-white"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
          aria-pressed={operationType === undefined}
          data-testid="operation-type-all"
        >
          All
        </button>
        {OPERATION_TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() =>
              onOperationTypeChange(
                operationType === t.value ? undefined : t.value,
              )
            }
            className={`rounded-full px-3 py-1 text-caption font-medium transition-colors ${
              operationType === t.value
                ? "bg-neutral-700 text-white"
                : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
            }`}
            aria-pressed={operationType === t.value}
            data-testid={`operation-type-${t.value}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Separator */}
      <span className="text-neutral-300" aria-hidden="true">
        |
      </span>

      {/* Active techs only toggle — on by default */}
      <label className="flex cursor-pointer items-center gap-2 text-caption text-neutral-700">
        <input
          type="checkbox"
          checked={activeTechsOnly}
          onChange={(e) => onActiveTechsOnlyChange(e.target.checked)}
          className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-600"
          data-testid="active-techs-only-toggle"
        />
        Active techs only
      </label>
    </div>
  );
}
