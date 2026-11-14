"use client";

/**
 * PilotPaginator — web-only pagination control
 *
 * Location: apps/web/src/components/PilotPaginator.tsx
 *
 * UI-FIX-1C: Created for server-side pagination on all 5 list pages.
 * Lives here (not packages/ui/) — web-specific, mobile uses infinite scroll.
 *
 * Renders nothing when total <= limit (single page).
 * Page input is uncontrolled (key=currentPage) — remounts when page changes externally.
 */

import React from "react";

interface PilotPaginatorProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (newOffset: number) => void;
}

export function PilotPaginator({
  total,
  limit,
  offset,
  onPageChange,
}: PilotPaginatorProps) {
  // Compute derived values — all before the early return
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const lastOffset = Math.floor((total - 1) / limit) * limit;

  // Hide when all results fit on one page
  if (total <= limit) return null;

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      const page = parseInt(e.currentTarget.value, 10);
      if (!isNaN(page) && page >= 1 && page <= totalPages) {
        onPageChange((page - 1) * limit);
      } else {
        // Reset to current page on invalid input
        e.currentTarget.value = String(currentPage);
      }
    }
  }

  const btnClass =
    "px-2 py-1 text-sm text-neutral-600 border border-neutral-200 rounded hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div
      className="flex items-center gap-2 mt-4 justify-center"
      data-testid="pilot-paginator"
    >
      <button
        className={btnClass}
        onClick={() => onPageChange(0)}
        disabled={offset === 0}
        aria-label="First page"
      >
        «
      </button>
      <button
        className={btnClass}
        onClick={() => onPageChange(Math.max(0, offset - limit))}
        disabled={offset === 0}
        aria-label="Previous page"
      >
        ‹
      </button>
      <span className="flex items-center gap-1 text-sm text-neutral-600">
        Page{" "}
        {/*
         * key=currentPage causes the input to remount with a fresh defaultValue
         * whenever the page changes via button navigation — no setState-in-effect needed.
         */}
        <input
          key={currentPage}
          type="number"
          defaultValue={currentPage}
          onKeyDown={handleInputKeyDown}
          className="w-12 px-1 py-0.5 text-center border border-neutral-300 rounded text-sm"
          min={1}
          max={totalPages}
          aria-label="Page number"
        />{" "}
        of {totalPages}
      </span>
      <button
        className={btnClass}
        onClick={() => onPageChange(offset + limit)}
        disabled={offset + limit >= total}
        aria-label="Next page"
      >
        ›
      </button>
      <button
        className={btnClass}
        onClick={() => onPageChange(lastOffset)}
        disabled={offset >= lastOffset}
        aria-label="Last page"
      >
        »
      </button>
    </div>
  );
}
