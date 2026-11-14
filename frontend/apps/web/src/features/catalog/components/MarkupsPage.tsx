/**
 * MarkupsPage — /catalog/markups
 *
 * Location: apps/web/src/features/catalog/components/MarkupsPage.tsx
 *
 * FE-B28: Migrated from manual <table> to TanStack Table v8.
 * Shows active markup versions per category.
 * "Set Markup" button opens SetMarkupModal (temporal supersession).
 */

"use client";

import React, { useState, useMemo } from "react";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import { LoadingState, ErrorState, EmptyState, RoleGate } from "@pilot/ui";
import { useMarkups } from "../hooks/useMarkups";
import type { TenantMarkupVersion } from "../hooks/useMarkups";
import { SetMarkupModal } from "./SetMarkupModal";
import { PilotTable } from "../../../components/PilotTable";

const columnHelper = createColumnHelper<TenantMarkupVersion>();

export function MarkupsPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const { data, isLoading, isError } = useMarkups();

  const markups = useMemo(() => data?.items ?? [], [data]);

  const columns = useMemo(
    () => [
      columnHelper.accessor("job_expense_category_code", {
        header: "Category",
        size: 200,
        minSize: 120,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="font-medium text-neutral-900 capitalize line-clamp-1">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor("markup_pct", {
        header: "Current Markup",
        size: 150,
        minSize: 90,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-right text-neutral-900 tabular-nums whitespace-nowrap block">
            {info.getValue()}%
          </span>
        ),
      }),
      columnHelper.accessor("valid_period_lower", {
        header: "Effective From",
        size: 160,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => {
          const val = info.getValue();
          return (
            <span className="text-neutral-500 whitespace-nowrap">
              {val
                ? new Date(val).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })
                : "—"}
            </span>
          );
        },
      }),
    ],
    [],
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: markups,
    columns,
    state: { sorting, columnSizing },
    onSortingChange: setSorting,
    onColumnSizingChange: setColumnSizing,
    columnResizeMode: "onChange",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) return <LoadingState type="full-page" />;
  if (isError) return <ErrorState type="server" />;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-neutral-900">
          Markup Percentages
        </h2>
        <RoleGate permission="catalog.manage">
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            + Set Markup
          </button>
        </RoleGate>
      </div>

      {markups.length === 0 ? (
        <EmptyState
          type="no-data"
          description="No markups configured yet. Set your first markup to enable automatic pricing."
        />
      ) : (
        <PilotTable table={table} />
      )}

      <SetMarkupModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
