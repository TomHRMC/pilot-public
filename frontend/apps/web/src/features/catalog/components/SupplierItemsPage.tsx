/**
 * SupplierItemsPage — /catalog/supplier-items
 *
 * Location: apps/web/src/features/catalog/components/SupplierItemsPage.tsx
 *
 * FE-B28: Migrated from manual <table> to TanStack Table v8.
 * Read-only list of supplier items synced by background process (Celery).
 * No create/edit actions — MVP scope is view-only.
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
import { LoadingState, ErrorState, EmptyState } from "@pilot/ui";
import { useSupplierItems } from "../hooks/useSupplierItems";
import type { SupplierItem } from "../hooks/useSupplierItems";
import { PilotTable } from "../../../components/PilotTable";

const columnHelper = createColumnHelper<SupplierItem>();

const columns = [
  columnHelper.accessor("sku", {
    header: "SKU",
    size: 120,
    minSize: 80,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span className="font-mono text-xs text-neutral-700 whitespace-nowrap">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("name", {
    header: "Name",
    size: 180,
    minSize: 100,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span className="font-medium text-neutral-900 line-clamp-2">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("description", {
    header: "Description",
    size: 260,
    minSize: 100,
    enableResizing: true,
    enableSorting: false,
    cell: (info) => (
      <span className="text-neutral-500 line-clamp-2">
        {info.getValue() ?? "—"}
      </span>
    ),
  }),
  columnHelper.accessor("is_active", {
    header: "Status",
    size: 100,
    minSize: 70,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span
        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
          info.getValue()
            ? "bg-success-50 text-success-700"
            : "bg-neutral-100 text-neutral-500"
        }`}
      >
        {info.getValue() ? "Active" : "Inactive"}
      </span>
    ),
  }),
];

export function SupplierItemsPage() {
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const { data: items, isLoading, isError } = useSupplierItems(search);

  const data = useMemo(() => items ?? [], [items]);

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
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
        <div>
          <h2 className="text-xl font-semibold text-neutral-900">
            Supplier Items
          </h2>
          <p className="mt-1 text-sm text-neutral-500">
            Items synced from your supplier catalogs. Read-only.
          </p>
        </div>
      </div>

      <div className="mb-4">
        <input
          type="search"
          placeholder="Search supplier items…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600"
          aria-label="Search supplier items"
        />
      </div>

      {!items || items.length === 0 ? (
        <EmptyState
          type="not-yet-set-up"
          title="No supplier items yet"
          description="Supplier items appear here after your catalog syncs."
        />
      ) : (
        <PilotTable table={table} />
      )}
    </div>
  );
}
