/**
 * PendingInboxFilterBar — filter controls for pending quotes inbox
 *
 * Location: apps/web/src/features/quote-approval/components/PendingInboxFilterBar.tsx
 */

"use client";

import React from "react";
import type { PendingQuoteFilters } from "../hooks/usePendingQuotes";

interface PendingInboxFilterBarProps {
  filters: PendingQuoteFilters;
  onFiltersChange: (filters: PendingQuoteFilters) => void;
}

export function PendingInboxFilterBar({
  filters,
  onFiltersChange,
}: PendingInboxFilterBarProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 pb-4 border-b border-neutral-200"
      role="search"
      aria-label="Filter pending quotes"
    >
      {/* Customer search */}
      <div className="flex items-center gap-2">
        <label
          htmlFor="customer-search"
          className="text-body text-neutral-600 whitespace-nowrap"
        >
          Customer
        </label>
        <input
          id="customer-search"
          type="search"
          placeholder="Search customer..."
          value={filters.customerSearch ?? ""}
          onChange={(e) =>
            onFiltersChange({
              ...filters,
              customerSearch: e.target.value || undefined,
            })
          }
          className="border border-neutral-200 rounded-md px-3 py-1.5 text-body text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-600 w-48"
          aria-label="Search by customer name"
        />
      </div>

      {/* Sort by age */}
      <fieldset className="flex items-center gap-2">
        <legend className="text-body text-neutral-600 mr-1">Sort</legend>
        {(["newest", "oldest"] as const).map((opt) => (
          <label
            key={opt}
            className="flex items-center gap-1.5 text-body text-neutral-900 cursor-pointer"
          >
            <input
              type="radio"
              name="sort-by"
              value={opt}
              checked={(filters.sortBy ?? "newest") === opt}
              onChange={() => onFiltersChange({ ...filters, sortBy: opt })}
              className="accent-brand-600"
              aria-label={`Sort by ${opt} first`}
            />
            {opt.charAt(0).toUpperCase() + opt.slice(1)}
          </label>
        ))}
      </fieldset>

      {/* Clear filters */}
      {(filters.customerSearch || filters.sortBy) && (
        <button
          type="button"
          onClick={() => onFiltersChange({})}
          className="text-body text-brand-600 hover:text-brand-800 underline ml-auto"
          aria-label="Clear all filters"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
