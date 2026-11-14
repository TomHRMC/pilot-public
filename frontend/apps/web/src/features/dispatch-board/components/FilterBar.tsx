/**
 * FilterBar — Horizontal collapsible filter bar for the dispatch board
 *
 * Location: apps/web/src/features/dispatch-board/components/FilterBar.tsx
 *
 * Replaces the fixed 192px left FilterSidebar with a full-width horizontal
 * strip docked between UnassignedTray and the board grid.
 *
 * Controls (left→right, expanded):
 *   Status pills  |  Priority segmented  |  Techs ▾ popover  |
 *   Customer Type  |  Job Type (conditional)  |
 *   N filters active  Clear all  [collapse ▾]
 *
 * Collapsed render: "Filters ▾" + active-count badge only.
 *
 * DISPATCH-B2 — new component
 * Per batch-dispatch-b2-design.md §H + §F
 * Decisions: dispatch-filter-redesign-decisions.md D1–D9 + D-DISC-1
 */

"use client";

import React from "react";
import { ChevronUpIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import { FilterPill } from "./FilterPill";
import { TechFilterPopover } from "./TechFilterPopover";
import type { DispatchBoardFilters } from "../store";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";

// ─── Status pill config (D-DISC-1) ───────────────────────────────────────────
// These MUST be valid DispatchBoardJob["status"] union members.
const STATUS_PILLS: Array<{
  label: string;
  value: DispatchBoardJob["status"];
}> = [
  { label: "Unassigned", value: "unassigned" },
  { label: "Scheduled", value: "scheduled" },
  { label: "Confirmed", value: "confirmed" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
];

// DISPATCH-B3: corrected priority values — standard/urgent/emergency (was rush/warranty/standard)
const PRIORITY_PILLS: Array<{
  label: string;
  value: "standard" | "urgent" | "emergency";
}> = [
  { label: "Standard", value: "standard" },
  { label: "Urgent", value: "urgent" },
  { label: "Emergency", value: "emergency" },
];

// DISPATCH-B3: corrected customer type values — person/company (was commercial/residential)
// "commercial/residential" is now site_type (display-only in dispatch panel, not a filter)
const CUSTOMER_TYPE_PILLS: Array<{
  label: string;
  value: "person" | "company";
}> = [
  { label: "Person", value: "person" },
  { label: "Company", value: "company" },
];

// ─── Props ────────────────────────────────────────────────────────────────────

export interface FilterBarProps {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  filters: DispatchBoardFilters;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onToggleTech: (id: string) => void;
  onToggleStatus: (s: DispatchBoardJob["status"]) => void;
  /** DISPATCH-B3: person/company (was commercial/residential) */
  onToggleCustomerType: (t: "person" | "company") => void;
  onToggleJobType: (t: string) => void;
  /** DISPATCH-B3: standard/urgent/emergency (was rush/standard/warranty) */
  onTogglePriority: (p: "standard" | "urgent" | "emergency") => void;
  /** Called when "All" status pill is clicked — resets only the status dimension */
  onResetStatus: () => void;
  onClearAll: () => void;
}

// ─── Separator ────────────────────────────────────────────────────────────────

function Separator() {
  return <span className="h-5 w-px bg-neutral-200" aria-hidden="true" />;
}

// ─── FilterBar ────────────────────────────────────────────────────────────────

/**
 * FilterBar
 *
 * Full-width horizontal bar docked between UnassignedTray and the board grid.
 * Collapsed/expanded state is managed by the parent (DispatchBoardPage local useState).
 * All filter dimensions backed by the existing DispatchBoardFilters Zustand state.
 */
export function FilterBar({
  techs,
  jobs,
  filters,
  collapsed,
  onToggleCollapsed,
  onToggleTech,
  onToggleStatus,
  onToggleCustomerType,
  onToggleJobType,
  onTogglePriority,
  onResetStatus,
  onClearAll,
}: FilterBarProps) {
  // ── Active filter count ────────────────────────────────────────────────────
  const activeCount =
    filters.techIds.length +
    filters.statuses.length +
    filters.customerTypes.length +
    filters.jobTypes.length +
    filters.priorities.length;

  const hasActiveFilters = activeCount > 0;

  // ── Unique job types — DISPATCH-B3: source from job_type_code/job_type_label.
  // Filter value = code (for applyFilters comparison); display label = job_type_label.
  const uniqueJobTypeEntries = Array.from(
    new Map(
      jobs
        .filter((j) => j.job_type_code)
        .map((j) => [
          j.job_type_code!,
          {
            code: j.job_type_code!,
            label: j.job_type_label ?? j.job_type_code!,
          },
        ]),
    ).values(),
  );

  // ── Collapsed render ───────────────────────────────────────────────────────
  if (collapsed) {
    return (
      <div
        className="w-full border-b border-neutral-200 bg-white px-4 py-2 flex items-center gap-2"
        aria-label="Dispatch board filter bar (collapsed)"
      >
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="inline-flex items-center gap-1 text-caption font-medium text-neutral-700 hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded"
          title="Expand filters"
        >
          Filters
          {activeCount > 0 && (
            <span className="text-caption text-neutral-500 tabular-nums">
              · {activeCount}
            </span>
          )}
          <ChevronDownIcon
            className="w-3.5 h-3.5 ml-0.5 text-neutral-400"
            aria-hidden="true"
          />
        </button>
      </div>
    );
  }

  // ── Expanded render ────────────────────────────────────────────────────────
  return (
    <div
      className="w-full border-b border-neutral-200 bg-white px-4 py-2 flex items-center gap-3 flex-wrap"
      aria-label="Dispatch board filter bar"
    >
      {/* ── Status pills ──────────────────────────────────────────────────── */}
      <div className="inline-flex bg-neutral-100 rounded-md p-0.5 gap-0.5">
        {/* "All" pill — clears only the status dimension */}
        <FilterPill
          label="All"
          active={filters.statuses.length === 0}
          onClick={onResetStatus}
        />
        {STATUS_PILLS.map(({ label, value }) => (
          <FilterPill
            key={value}
            label={label}
            active={filters.statuses.includes(value)}
            onClick={() => onToggleStatus(value)}
          />
        ))}
      </div>

      <Separator />

      {/* ── Priority segmented control ────────────────────────────────────── */}
      <div className="inline-flex bg-neutral-100 rounded-md p-0.5 gap-0.5">
        {PRIORITY_PILLS.map(({ label, value }) => (
          <FilterPill
            key={value}
            label={label}
            active={filters.priorities.includes(value)}
            onClick={() => onTogglePriority(value)}
          />
        ))}
      </div>

      <Separator />

      {/* ── Tech filter popover ───────────────────────────────────────────── */}
      <TechFilterPopover
        techs={techs}
        selectedTechIds={filters.techIds}
        onToggleTech={onToggleTech}
      />

      <Separator />

      {/* ── Customer Type ─────────────────────────────────────────────────── */}
      <div className="inline-flex bg-neutral-100 rounded-md p-0.5 gap-0.5">
        {CUSTOMER_TYPE_PILLS.map(({ label, value }) => (
          <FilterPill
            key={value}
            label={label}
            active={filters.customerTypes.includes(value)}
            onClick={() => onToggleCustomerType(value)}
          />
        ))}
      </div>

      {/* ── Job Type (conditional) ────────────────────────────────────────── */}
      {uniqueJobTypeEntries.length > 0 && (
        <>
          <Separator />
          <div className="inline-flex bg-neutral-100 rounded-md p-0.5 gap-0.5">
            {uniqueJobTypeEntries.map(({ code, label }) => (
              <FilterPill
                key={code}
                label={label}
                active={filters.jobTypes.includes(code)}
                onClick={() => onToggleJobType(code)}
              />
            ))}
          </div>
        </>
      )}

      {/* ── Active count + Clear all ──────────────────────────────────────── */}
      {hasActiveFilters && (
        <>
          <Separator />
          <span className="text-caption text-neutral-500">
            {activeCount} {activeCount === 1 ? "filter" : "filters"} active
          </span>
          <button
            type="button"
            onClick={onClearAll}
            className="text-caption text-brand-600 hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded"
          >
            Clear all
          </button>
        </>
      )}

      {/* ── Collapse toggle (far right) ───────────────────────────────────── */}
      <button
        type="button"
        onClick={onToggleCollapsed}
        className="ml-auto p-1 rounded text-neutral-400 hover:text-neutral-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        title="Collapse filters"
      >
        <ChevronUpIcon className="w-4 h-4" aria-hidden="true" />
      </button>
    </div>
  );
}
