/**
 * LaborRatesPage — /catalog/labor-rates
 *
 * Location: apps/web/src/features/catalog/components/LaborRatesPage.tsx
 *
 * FE-B28: Migrated from manual <table> to TanStack Table v8.
 * Shows active labor rate versions with burdened rate display.
 * "Set Rate" button opens SetLaborRateModal (temporal supersession).
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
import { useLaborRates } from "../hooks/useLaborRates";
import type { LaborRateVersion } from "../hooks/useLaborRates";
import { SetLaborRateModal } from "./SetLaborRateModal";
import { PilotTable } from "../../../components/PilotTable";

const columnHelper = createColumnHelper<LaborRateVersion>();

export function LaborRatesPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const { data: rates, isLoading, isError } = useLaborRates();

  const columns = useMemo(
    () => [
      columnHelper.accessor("skill_level_code", {
        header: "Skill Level",
        size: 160,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="font-medium text-neutral-900 capitalize line-clamp-1">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor("hourly_rate_cents", {
        header: "Hourly Rate",
        size: 120,
        minSize: 80,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-right text-neutral-900 tabular-nums whitespace-nowrap block">
            ${(info.getValue() / 100).toFixed(2)}/hr
          </span>
        ),
      }),
      columnHelper.accessor("burden_pct", {
        header: "Burden %",
        size: 100,
        minSize: 70,
        enableResizing: true,
        enableSorting: true,
        sortingFn: (a, b) =>
          parseFloat(a.original.burden_pct) - parseFloat(b.original.burden_pct),
        cell: (info) => (
          <span className="text-neutral-600 tabular-nums whitespace-nowrap">
            {(parseFloat(info.getValue()) * 100).toFixed(1)}%
          </span>
        ),
      }),
      columnHelper.accessor("burdened_rate_cents", {
        header: "Burdened Rate",
        size: 140,
        minSize: 90,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-right font-medium text-neutral-900 tabular-nums whitespace-nowrap block">
            ${(info.getValue() / 100).toFixed(2)}/hr
          </span>
        ),
      }),
      columnHelper.accessor("valid_period_lower", {
        header: "Effective From",
        size: 140,
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
    data: rates ?? [],
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
        <h2 className="text-xl font-semibold text-neutral-900">Labor Rates</h2>
        <RoleGate permission="catalog.manage">
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            + Set Rate
          </button>
        </RoleGate>
      </div>

      {!rates || rates.length === 0 ? (
        <EmptyState
          type="no-data"
          description="No labor rates configured yet. Set your first rate to enable accurate job costing."
        />
      ) : (
        <PilotTable table={table} />
      )}

      <SetLaborRateModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
