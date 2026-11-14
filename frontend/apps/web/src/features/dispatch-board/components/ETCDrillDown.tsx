/**
 * ETCDrillDown — Quote line × hours captured / hours remaining table
 *
 * Location: apps/web/src/features/dispatch-board/components/ETCDrillDown.tsx
 *
 * Tech-by-tech breakdown expandable.
 * Click row to filter time entries.
 * Over-quote lines highlighted.
 *
 * Per batch-fe-b4-design.md §A.2.5
 */

"use client";

import React, { useState } from "react";
import type { QuoteLine } from "../hooks/useJobDetail";
import { ETCLineRow } from "./ETCLineRow";

interface ETCDrillDownProps {
  quoteLines: QuoteLine[];
  onLineSelect?: (lineId: string) => void;
}

/**
 * ETCDrillDown
 *
 * Table showing ETC status per quote line with tech breakdown.
 * Empty state when no ETC data is available (BE-B3 pending).
 */
export function ETCDrillDown({ quoteLines, onLineSelect }: ETCDrillDownProps) {
  const [expandedLines, setExpandedLines] = useState<Set<string>>(new Set());

  const toggleLine = (lineId: string) => {
    setExpandedLines((prev) => {
      const next = new Set(prev);
      if (next.has(lineId)) {
        next.delete(lineId);
      } else {
        next.add(lineId);
      }
      return next;
    });
    onLineSelect?.(lineId);
  };

  if (quoteLines.length === 0) {
    return (
      <div className="py-4 text-center">
        <p className="text-body text-neutral-400">No ETC data available</p>
        <p className="text-caption text-neutral-400 mt-1">
          ETC tracking requires active quote lines.
        </p>
      </div>
    );
  }

  const totalQuoted = quoteLines.reduce((s, l) => s + l.quoted_hours, 0);
  const totalActual = quoteLines.reduce((s, l) => s + l.actual_hours, 0);
  const totalRemaining = quoteLines.reduce((s, l) => s + l.remaining_hours, 0);

  return (
    <div>
      <table
        className="w-full text-sm"
        aria-label="ETC drill-down by quote line"
      >
        <thead>
          <tr className="border-b border-neutral-200">
            <th className="py-1.5 pl-3 pr-2 text-left text-caption font-medium text-neutral-600">
              Line Item
            </th>
            <th className="py-1.5 px-2 text-right text-caption font-medium text-neutral-600">
              Quoted
            </th>
            <th className="py-1.5 px-2 text-right text-caption font-medium text-neutral-600">
              Actual
            </th>
            <th className="py-1.5 pl-2 pr-3 text-right text-caption font-medium text-neutral-600">
              Remaining
            </th>
          </tr>
        </thead>
        <tbody>
          {quoteLines.map((line) => (
            <ETCLineRow
              key={line.id}
              quoteLine={line}
              isExpanded={expandedLines.has(line.id)}
              onToggle={() => toggleLine(line.id)}
            />
          ))}
        </tbody>
        {/* Totals footer */}
        <tfoot>
          <tr className="border-t border-neutral-200 bg-neutral-50">
            <td className="py-2 pl-3 pr-2 text-body font-medium text-neutral-900">
              Total
            </td>
            <td className="py-2 px-2 text-right text-body font-medium text-neutral-900 tabular-nums">
              {totalQuoted.toFixed(1)}h
            </td>
            <td className="py-2 px-2 text-right text-body font-medium tabular-nums">
              <span
                className={
                  totalActual > totalQuoted
                    ? "text-fault-600"
                    : "text-neutral-900"
                }
              >
                {totalActual.toFixed(1)}h
              </span>
            </td>
            <td className="py-2 pl-2 pr-3 text-right text-body font-medium text-neutral-900 tabular-nums">
              {totalRemaining.toFixed(1)}h
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
