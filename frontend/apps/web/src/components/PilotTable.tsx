"use client";
// "use no memo" — opt this component out of React Compiler memoisation.
// The React Compiler (reactCompiler: true in next.config.ts) aggressively memoises
// components and their sub-expressions. PilotTable receives a TanStack Table instance
// whose internal state changes on every sort/resize event, but the Compiler sees the
// `table` prop reference as stable and skips re-renders, so sort indicators never update.
// This directive is the official escape hatch: https://react.dev/learn/react-compiler#opt-out
"use no memo";

/**
 * PilotTable — shared TanStack Table render wrapper
 *
 * Location: apps/web/src/components/PilotTable.tsx
 *
 * FE-B28: Accepts a TanStack Table<TData> instance and renders the complete
 * <table> markup including sort indicators and column resize handles.
 *
 * DOES NOT render: empty states, filter UIs, page headers, modals, or Load More.
 * Those remain in the individual page components.
 */

import React from "react";
import { flexRender, type Table } from "@tanstack/react-table";

interface PilotTableProps<TData> {
  table: Table<TData>;
  /** Optional extra CSS classes on the outer container */
  className?: string;
  /** Optional data-testid applied to the <table> element (e.g. "recent-comms-table") */
  tableDataTestId?: string;
  /** Optional factory that returns a data-testid for each <tr> (e.g. `comm-row-${id}`) */
  getRowDataTestId?: (row: TData) => string | undefined;
  /**
   * Optional factory that returns extra CSS classes for each <tr> based on the
   * row data (e.g. alert-level row styling). The returned classes are merged
   * with the default hover/transition classes — if the returned string includes
   * its own hover class, it overrides the default.
   * C-B11: used by the cohort dashboard for red/amber alert row tinting.
   */
  getRowClassName?: (row: TData) => string | undefined;
}

export function PilotTable<TData>({
  table,
  className = "",
  tableDataTestId,
  getRowDataTestId,
  getRowClassName,
}: PilotTableProps<TData>): React.ReactElement {
  return (
    <div
      className={`overflow-x-auto rounded-lg border border-neutral-200 bg-white ${className}`}
    >
      {/* Table stretches to 100% of container; column sizes are used as
          proportional flex-weights (%) so columns fill available width. */}
      <table
        className="w-full table-fixed"
        style={{ width: "100%" }}
        data-testid={tableDataTestId}
      >
        <thead className="bg-neutral-50 border-b border-neutral-200">
          {table.getHeaderGroups().map((headerGroup) => {
            const totalSize = headerGroup.headers.reduce(
              (sum, h) => sum + h.getSize(),
              0,
            );
            return (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const pct =
                    totalSize > 0
                      ? `${((header.getSize() / totalSize) * 100).toFixed(2)}%`
                      : undefined;
                  return (
                    <th
                      key={header.id}
                      style={{ width: pct, position: "relative" }}
                      className={`px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide select-none ${
                        header.column.getCanSort()
                          ? "cursor-pointer hover:bg-neutral-100 transition-colors"
                          : ""
                      }`}
                      onClick={(e) => {
                        // Wrap in an arrow so the React Compiler doesn't cache a stale
                        // handler reference across renders (reactCompiler: true in next.config.ts
                        // aggressively memoises direct function-call return values).
                        header.column.getToggleSortingHandler()?.(e);
                      }}
                    >
                      <span className="flex items-center gap-1">
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                        {header.column.getCanSort() && (
                          <span className="text-neutral-400 ml-0.5">
                            {header.column.getIsSorted() === "asc"
                              ? "▲"
                              : header.column.getIsSorted() === "desc"
                                ? "▼"
                                : "↕"}
                          </span>
                        )}
                      </span>
                      {/* Column resize handle — stopPropagation prevents the th onClick
                      (sort toggle) from firing when the user starts a resize drag */}
                      {header.column.getCanResize() && (
                        <div
                          onMouseDown={(e) => {
                            e.stopPropagation();
                            header.getResizeHandler()(e);
                          }}
                          onTouchStart={(e) => {
                            e.stopPropagation();
                            header.getResizeHandler()(e);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className={`absolute right-0 top-0 h-full w-1 cursor-col-resize select-none touch-none transition-opacity ${
                            header.column.getIsResizing()
                              ? "bg-brand-400 opacity-100"
                              : "bg-neutral-300 opacity-0 hover:opacity-100"
                          }`}
                        />
                      )}
                    </th>
                  );
                })}
              </tr>
            );
          })}
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {table.getRowModel().rows.map((row) => {
            const rowClassName = getRowClassName?.(row.original);
            return (
              <tr
                key={row.id}
                className={
                  rowClassName ?? "hover:bg-neutral-50 transition-colors"
                }
                data-testid={getRowDataTestId?.(row.original)}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
