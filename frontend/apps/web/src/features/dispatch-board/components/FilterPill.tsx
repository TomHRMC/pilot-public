/**
 * FilterPill — Presentational pill for dispatch board FilterBar
 *
 * Location: apps/web/src/features/dispatch-board/components/FilterPill.tsx
 *
 * Mirrors the PillToggle visual from DispatchToolbar.tsx:90.
 * Shared by status / priority / customer-type / job-type rows in FilterBar.
 *
 * DISPATCH-B2 — new component
 * Per batch-dispatch-b2-design.md §H + §F
 */

"use client";

import React from "react";

export interface FilterPillProps {
  label: string;
  active: boolean;
  onClick: () => void;
  /** Optional trailing count badge (deferred nice-to-have per design §G) */
  count?: number;
  /** Data-driven tech color dot — the ONE allowed inline style (API-sourced hex) */
  colorDot?: string;
}

/**
 * FilterPill
 *
 * Stateless pill button. Active state mirrors PillToggle from DispatchToolbar.
 * Zero hardcoded design values — all tokens from pilotPreset.
 */
export function FilterPill({
  label,
  active,
  onClick,
  count,
  colorDot,
}: FilterPillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "px-2.5 py-1 text-caption font-medium rounded",
        "focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:outline-none",
        "inline-flex items-center gap-1",
        active
          ? "bg-white shadow-sm text-neutral-900"
          : "text-neutral-500 hover:text-neutral-700",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Data-driven color dot — only allowed inline style */}
      {colorDot && (
        <span
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: colorDot }}
          aria-hidden="true"
        />
      )}

      {label}

      {/* Optional per-option count */}
      {count !== undefined && (
        <span className="text-caption text-neutral-400 tabular-nums ml-0.5">
          {count}
        </span>
      )}
    </button>
  );
}
