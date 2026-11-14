/**
 * PricebookItemsPage — catalog pricebook list with search, status filter, add, edit, update price
 *
 * Location: apps/web/src/features/catalog/components/PricebookItemsPage.tsx
 *
 * UI-FIX-1C: Added server-side search + status dropdown + PilotPaginator.
 * Replaced Live More with PilotPaginator.
 * FE-B28: TanStack Table v8 (preserved).
 * FE-B20: /catalog (default tab).
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
import { usePricebook } from "../hooks/usePricebook";
import { useCreatePricebookItem } from "../hooks/useCreatePricebookItem";
import { useUpdatePricebookItem } from "../hooks/useUpdatePricebookItem";
import { PricebookItemForm } from "./PricebookItemForm";
import { UpdatePriceModal } from "./UpdatePriceModal";
import type { PricebookItem } from "../hooks/usePricebook";
import type { PricebookItemFormValues } from "./PricebookItemForm";
import { PilotTable } from "../../../components/PilotTable";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

type ModalState =
  | { type: "closed" }
  | { type: "create" }
  | { type: "edit"; item: PricebookItem }
  | { type: "update-price"; item: PricebookItem };

const columnHelper = createColumnHelper<PricebookItem>();

export function PricebookItemsPage() {
  // Filter input state (not yet applied)
  const [searchInput, setSearchInput] = useState("");
  const [statusInput, setStatusInput] = useState<"active" | "inactive" | "">(
    "",
  );

  // Applied state — triggers API fetch
  const [appliedSearch, setAppliedSearch] = useState<string | undefined>(
    undefined,
  );
  const [appliedStatus, setAppliedStatus] = useState<
    "active" | "inactive" | ""
  >("");
  const [offset, setOffset] = useState(0);

  const [modalState, setModalState] = useState<ModalState>({ type: "closed" });
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

  const {
    data: pricebookData,
    isLoading,
    isError,
  } = usePricebook({
    search: appliedSearch,
    offset,
    limit: LIST_PAGE_SIZE,
    status: appliedStatus || undefined,
  });
  const items = pricebookData?.items ?? [];
  const total = pricebookData?.total ?? 0;

  const createMutation = useCreatePricebookItem();
  const updateMutation = useUpdatePricebookItem();

  function handleSearch() {
    setOffset(0);
    setAppliedSearch(searchInput.trim() || undefined);
    setAppliedStatus(statusInput);
  }

  function handleClear() {
    setSearchInput("");
    setStatusInput("");
    setOffset(0);
    setAppliedSearch(undefined);
    setAppliedStatus("");
  }

  const hasActiveFilters = !!appliedSearch || !!appliedStatus;

  function handleCreateSubmit(values: PricebookItemFormValues) {
    const priceCents = Math.round(
      parseFloat(values.initial_price_dollars) * 100,
    );
    createMutation.mutate(
      {
        sku: values.sku,
        name: values.name,
        description: values.description || null,
        taxability_code: values.taxability_code || null,
        initial_price_cents: priceCents,
      },
      { onSuccess: () => setModalState({ type: "closed" }) },
    );
  }

  function handleEditSubmit(itemId: string, values: PricebookItemFormValues) {
    updateMutation.mutate(
      {
        itemId,
        payload: {
          name: values.name,
          description: values.description || null,
          taxability_code: values.taxability_code || null,
        },
      },
      { onSuccess: () => setModalState({ type: "closed" }) },
    );
  }

  const columns = useMemo(
    () => [
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
        size: 200,
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
        size: 240,
        minSize: 100,
        enableResizing: true,
        enableSorting: false,
        cell: (info) => (
          <span className="text-neutral-500 line-clamp-2">
            {info.getValue() ?? "—"}
          </span>
        ),
      }),
      columnHelper.accessor("current_price", {
        header: "Current Price",
        size: 130,
        minSize: 80,
        enableResizing: true,
        enableSorting: true,
        sortingFn: (a, b) => {
          const aPrice =
            a.original.current_price?.default_unit_price_cents ?? 0;
          const bPrice =
            b.original.current_price?.default_unit_price_cents ?? 0;
          return aPrice - bPrice;
        },
        cell: (info) => {
          const price = info.getValue();
          return (
            <span className="text-right text-neutral-900 tabular-nums whitespace-nowrap block">
              {price
                ? `$${(price.default_unit_price_cents / 100).toFixed(2)}`
                : "—"}
            </span>
          );
        },
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
      columnHelper.display({
        id: "actions",
        header: "Actions",
        size: 160,
        minSize: 80,
        enableResizing: false,
        enableSorting: false,
        cell: (info) => {
          const item = info.row.original;
          return (
            <div className="flex items-center gap-2">
              <RoleGate permission="catalog.manage">
                <button
                  type="button"
                  onClick={() => setModalState({ type: "edit", item })}
                  className="text-xs text-brand-600 hover:text-brand-800 font-medium"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => setModalState({ type: "update-price", item })}
                  className="text-xs text-neutral-600 hover:text-neutral-900 font-medium"
                  title="Update price"
                >
                  💲 Update Price
                </button>
              </RoleGate>
            </div>
          );
        },
      }),
    ],
    [],
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: items,
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
          Pricebook Items
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-neutral-500">
            {total} item{total !== 1 ? "s" : ""}
          </span>
          <RoleGate permission="catalog.manage">
            <button
              type="button"
              onClick={() => setModalState({ type: "create" })}
              className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
            >
              + Add Item
            </button>
          </RoleGate>
        </div>
      </div>

      {/* UI-FIX-1C: filter bar with search + status dropdown */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Search</label>
          <input
            type="search"
            placeholder="Search name, SKU, description…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-72 rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600"
            aria-label="Search pricebook items"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Status</label>
          <select
            value={statusInput}
            onChange={(e) =>
              setStatusInput(e.target.value as "active" | "inactive" | "")
            }
            className="px-3 py-2 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-600 bg-white"
            aria-label="Filter by status"
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
            data-testid="catalog-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              data-testid="catalog-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState
          type={hasActiveFilters ? "no-results" : "no-data"}
          description={
            hasActiveFilters
              ? "No items match your search."
              : "Add your first pricebook item to get started."
          }
        />
      ) : (
        <>
          <PilotTable table={table} />
          <PilotPaginator
            total={total}
            limit={LIST_PAGE_SIZE}
            offset={offset}
            onPageChange={setOffset}
          />
        </>
      )}

      {/* Create modal */}
      {modalState.type === "create" && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-item-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          <div
            className="absolute inset-0 bg-neutral-900 opacity-40"
            onClick={() => setModalState({ type: "closed" })}
            aria-hidden="true"
          />
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2
                  id="add-item-modal-title"
                  className="text-lg font-semibold text-neutral-900"
                >
                  Add Pricebook Item
                </h2>
                <button
                  type="button"
                  onClick={() => setModalState({ type: "closed" })}
                  className="text-neutral-400 hover:text-neutral-600 transition-colors"
                  aria-label="Close modal"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <PricebookItemForm
                isEdit={false}
                onSubmit={handleCreateSubmit}
                onCancel={() => setModalState({ type: "closed" })}
                isSubmitting={createMutation.isPending}
                submitLabel="Add Item"
              />
            </div>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {modalState.type === "edit" && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-item-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          <div
            className="absolute inset-0 bg-neutral-900 opacity-40"
            onClick={() => setModalState({ type: "closed" })}
            aria-hidden="true"
          />
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2
                  id="edit-item-modal-title"
                  className="text-lg font-semibold text-neutral-900"
                >
                  Edit Pricebook Item
                </h2>
                <button
                  type="button"
                  onClick={() => setModalState({ type: "closed" })}
                  className="text-neutral-400 hover:text-neutral-600 transition-colors"
                  aria-label="Close modal"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <PricebookItemForm
                isEdit={true}
                initialValues={{
                  sku: modalState.item.sku,
                  name: modalState.item.name,
                  description: modalState.item.description ?? "",
                  taxability_code: modalState.item.taxability_code ?? "",
                }}
                currentPriceCents={
                  modalState.item.current_price?.default_unit_price_cents
                }
                onSubmit={(values) =>
                  handleEditSubmit(modalState.item.id, values)
                }
                onCancel={() => setModalState({ type: "closed" })}
                isSubmitting={updateMutation.isPending}
                submitLabel="Save Changes"
              />
            </div>
          </div>
        </div>
      )}

      {/* Update price modal */}
      {modalState.type === "update-price" && (
        <UpdatePriceModal
          open
          itemId={modalState.item.id}
          itemName={modalState.item.name}
          currentPriceCents={
            modalState.item.current_price?.default_unit_price_cents ?? 0
          }
          onClose={() => setModalState({ type: "closed" })}
        />
      )}
    </div>
  );
}
