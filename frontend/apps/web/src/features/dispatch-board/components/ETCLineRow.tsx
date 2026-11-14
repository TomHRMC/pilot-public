/**
 * ETCLineRow — Single row in the ETC drill-down table
 *
 * Location: apps/web/src/features/dispatch-board/components/ETCLineRow.tsx
 *
 * Shows labor line name, quoted hours, actual hours, remaining ETC.
 * Highlighted when over-quote.
 *
 * Per batch-fe-b4-design.md §A.2.5
 */

import React from "react";
import type { QuoteLine } from "../hooks/useJobDetail";

interface ETCLineRowProps {
  quoteLine: QuoteLine;
  isExpanded?: boolean;
  onToggle?: () => void;
}

/**
 * ETCLineRow
 *
 * Single row in the ETC drill-down table.
 * Uses token classes for over-quote highlighting.
 */
export function ETCLineRow({
  quoteLine,
  isExpanded = false,
  onToggle,
}: ETCLineRowProps) {
  const isOverQuote = quoteLine.actual_hours > quoteLine.quoted_hours;
  const hasBreakdowns = quoteLine.tech_breakdowns.length > 0;

  return (
    <>
      {/* Main row */}
      <tr
        className={[
          "border-b border-neutral-100",
          isOverQuote ? "bg-fault-50" : "hover:bg-neutral-50",
        ].join(" ")}
      >
        <td className="py-2 pl-3 pr-2">
          <div className="flex items-center gap-2">
            {hasBreakdowns && onToggle && (
              <button
                type="button"
                onClick={onToggle}
                className="p-0.5 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-1 focus-visible:ring-brand-600 rounded"
                aria-expanded={isExpanded}
                aria-label={`${isExpanded ? "Collapse" : "Expand"} ${quoteLine.description} tech breakdown`}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="currentColor"
                  className={`transition-transform ${isExpanded ? "rotate-90" : ""}`}
                  aria-hidden="true"
                >
                  <path
                    d="M4 2l4 4-4 4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                </svg>
              </button>
            )}
            <span
              className={`text-body truncate ${isOverQuote ? "text-fault-600" : "text-neutral-900"}`}
            >
              {quoteLine.description}
            </span>
          </div>
        </td>
        <td className="py-2 px-2 text-right text-body text-neutral-600 tabular-nums">
          {quoteLine.quoted_hours.toFixed(1)}h
        </td>
        <td className="py-2 px-2 text-right text-body tabular-nums">
          <span
            className={
              isOverQuote ? "text-fault-600 font-medium" : "text-neutral-900"
            }
          >
            {quoteLine.actual_hours.toFixed(1)}h
          </span>
        </td>
        <td className="py-2 pl-2 pr-3 text-right text-body text-neutral-600 tabular-nums">
          {quoteLine.remaining_hours.toFixed(1)}h
        </td>
      </tr>

      {/* Tech breakdown (expandable) */}
      {isExpanded &&
        quoteLine.tech_breakdowns.map((breakdown) => (
          <tr
            key={breakdown.tech_id}
            className="border-b border-neutral-50 bg-neutral-50"
          >
            <td className="py-1.5 pl-8 pr-2">
              <span className="text-caption text-neutral-600">
                {breakdown.tech_name}
              </span>
            </td>
            <td className="py-1.5 px-2 text-right text-caption text-neutral-400">
              —
            </td>
            <td className="py-1.5 px-2 text-right text-caption text-neutral-600 tabular-nums">
              {breakdown.hours.toFixed(1)}h
            </td>
            <td className="py-1.5 pl-2 pr-3 text-right text-caption text-neutral-400">
              —
            </td>
          </tr>
        ))}
    </>
  );
}
