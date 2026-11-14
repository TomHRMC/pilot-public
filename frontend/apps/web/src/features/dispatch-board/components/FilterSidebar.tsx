/**
 * FilterSidebar — Dispatch board filter sidebar
 *
 * Location: apps/web/src/features/dispatch-board/components/FilterSidebar.tsx
 *
 * Five filter groups: Tech, Status, Customer, Job Type, Priority.
 * Each checkbox shows a count of matching jobs.
 * Filter behavior: pure visibility filtering (hidden items remain in DB).
 *
 * Per batch-fe-b4-design.md §A.2.1
 * Per dispatch-board-spec.md §3 (Filter Sidebar)
 */

"use client";

import React from "react";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";
import type { DispatchBoardFilters } from "../store";

interface FilterSidebarProps {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  filters: DispatchBoardFilters;
  onToggleTech: (id: string) => void;
  onToggleStatus: (status: DispatchBoardFilters["statuses"][number]) => void;
  onToggleCustomerType: (
    type: DispatchBoardFilters["customerTypes"][number],
  ) => void;
  onToggleJobType: (type: string) => void;
  onTogglePriority: (
    priority: DispatchBoardFilters["priorities"][number],
  ) => void;
  onClearAll: () => void;
}

interface FilterGroupProps {
  label: string;
  children: React.ReactNode;
}

function FilterGroup({ label, children }: FilterGroupProps) {
  return (
    <div>
      <h3 className="text-caption font-medium text-neutral-400 uppercase tracking-wide mb-2">
        {label}
      </h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

interface FilterCheckboxProps {
  id: string;
  label: string;
  count: number;
  checked: boolean;
  onChange: () => void;
  colorDot?: string; // Data-driven from API
}

function FilterCheckbox({
  id,
  label,
  count,
  checked,
  onChange,
  colorDot,
}: FilterCheckboxProps) {
  return (
    <label
      htmlFor={id}
      className="flex items-center gap-2 py-1 px-1 rounded cursor-pointer hover:bg-neutral-50 group"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-3.5 h-3.5 rounded-sm border-neutral-300 text-brand-600 focus:ring-brand-600 focus:ring-offset-0 focus:ring-1 cursor-pointer"
      />
      {colorDot && (
        <span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: colorDot }}
          aria-hidden="true"
        />
      )}
      <span className="text-body text-neutral-700 flex-1 truncate">
        {label}
      </span>
      <span className="text-caption text-neutral-400 tabular-nums">
        {count}
      </span>
    </label>
  );
}

/**
 * FilterSidebar
 *
 * Left sidebar with five filter groups for the dispatch board.
 * State lives in useDispatchBoardStore — this component is display-only.
 */
export function FilterSidebar({
  techs,
  jobs,
  filters,
  onToggleTech,
  onToggleStatus,
  onToggleCustomerType,
  onToggleJobType,
  onTogglePriority,
  onClearAll,
}: FilterSidebarProps) {
  const hasActiveFilters =
    filters.techIds.length > 0 ||
    filters.statuses.length > 0 ||
    filters.customerTypes.length > 0 ||
    filters.jobTypes.length > 0 ||
    filters.priorities.length > 0;

  // DISPATCH-B3: source job types from job_type_code/job_type_label
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

  return (
    <aside
      className="w-48 flex-shrink-0 bg-white border-r border-neutral-200 overflow-y-auto"
      aria-label="Dispatch board filters"
    >
      <div className="p-3 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-body font-medium text-neutral-900">
            Filters
          </span>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onClearAll}
              className="text-caption text-brand-600 hover:text-brand-800 focus:outline-none focus-visible:ring-1 focus-visible:ring-brand-600 rounded"
            >
              Clear all
            </button>
          )}
        </div>

        {/* Tech filter */}
        <FilterGroup label="Tech">
          {techs.map((tech, idx) => (
            <FilterCheckbox
              key={tech.id ?? idx}
              id={`filter-tech-${tech.id}`}
              label={tech.name}
              count={jobs.filter((j) => j.tech_id === tech.id).length}
              checked={
                filters.techIds.length === 0 ||
                filters.techIds.includes(tech.id)
              }
              onChange={() => onToggleTech(tech.id)}
              colorDot={tech.display_color ?? undefined}
            />
          ))}
        </FilterGroup>

        {/* Status filter */}
        <FilterGroup label="Status">
          {(
            [
              { value: "unassigned", label: "Unassigned" },
              { value: "scheduled", label: "Scheduled" },
              { value: "in_progress", label: "In progress" },
              { value: "confirmed", label: "Confirmed" },
            ] as const
          ).map(({ value, label }) => (
            <FilterCheckbox
              key={value}
              id={`filter-status-${value}`}
              label={label}
              count={jobs.filter((j) => j.status === value).length}
              checked={
                filters.statuses.length === 0 ||
                filters.statuses.includes(value)
              }
              onChange={() => onToggleStatus(value)}
            />
          ))}
        </FilterGroup>

        {/* DISPATCH-B3: Customer type filter — person/company (was commercial/residential) */}
        <FilterGroup label="Customer Type">
          {(
            [
              { value: "person", label: "Person" },
              { value: "company", label: "Company" },
            ] as const
          ).map(({ value, label }) => (
            <FilterCheckbox
              key={value}
              id={`filter-customer-${value}`}
              label={label}
              count={jobs.filter((j) => j.customer_type === value).length}
              checked={
                filters.customerTypes.length === 0 ||
                filters.customerTypes.includes(value)
              }
              onChange={() => onToggleCustomerType(value)}
            />
          ))}
        </FilterGroup>

        {/* DISPATCH-B3: Job type filter — uses job_type_code/job_type_label */}
        {uniqueJobTypeEntries.length > 0 && (
          <FilterGroup label="Job Type">
            {uniqueJobTypeEntries.map(({ code, label }) => (
              <FilterCheckbox
                key={code}
                id={`filter-jobtype-${code}`}
                label={label}
                count={jobs.filter((j) => j.job_type_code === code).length}
                checked={
                  filters.jobTypes.length === 0 ||
                  filters.jobTypes.includes(code)
                }
                onChange={() => onToggleJobType(code)}
              />
            ))}
          </FilterGroup>
        )}

        {/* DISPATCH-B3: Priority filter — standard/urgent/emergency (was rush/warranty) */}
        <FilterGroup label="Priority">
          {(
            [
              { value: "standard", label: "Standard" },
              { value: "urgent", label: "Urgent" },
              { value: "emergency", label: "Emergency" },
            ] as const
          ).map(({ value, label }) => (
            <FilterCheckbox
              key={value}
              id={`filter-priority-${value}`}
              label={label}
              count={jobs.filter((j) => j.priority === value).length}
              checked={
                filters.priorities.length === 0 ||
                filters.priorities.includes(value)
              }
              onChange={() => onTogglePriority(value)}
            />
          ))}
        </FilterGroup>
      </div>
    </aside>
  );
}
