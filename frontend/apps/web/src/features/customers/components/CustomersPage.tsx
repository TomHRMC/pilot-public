"use client";

/**
 * CustomersPage — server-side paginated customer list with filter bar
 *
 * Location: apps/web/src/features/customers/components/CustomersPage.tsx
 *
 * UI-FIX-1C: Added filter bar (search + status dropdown) with explicit Search/Clear.
 * Replaced Load More pattern with PilotPaginator.
 * FE-B28: TanStack Table v8 (preserved).
 */

import React, { useState, useMemo, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import { useCustomers } from "../hooks/useCustomers";
import type { CustomerListItem } from "../hooks/useCustomers";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";
import { RoleGate } from "@pilot/ui/role-gate";
import { CreateCustomerModal } from "./CreateCustomerModal";
import { PilotTable } from "../../../components/PilotTable";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

const columnHelper = createColumnHelper<CustomerListItem>();

const columns = [
  columnHelper.accessor("display_name", {
    header: "Name",
    size: 220,
    minSize: 120,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <a
        href={`/customers/${info.row.original.id}`}
        className="text-brand-600 hover:underline font-medium line-clamp-2"
      >
        {info.getValue()}
      </a>
    ),
  }),
  columnHelper.accessor("type", {
    header: "Type",
    size: 120,
    minSize: 80,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span className="text-neutral-600 capitalize whitespace-nowrap">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("email", {
    header: "Email",
    size: 200,
    minSize: 120,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span className="text-neutral-600 line-clamp-1">
        {info.getValue() ?? "—"}
      </span>
    ),
  }),
];

export function CustomersPage() {
  // Filter input state (not yet applied — user clicks "Search")
  const [searchInput, setSearchInput] = useState("");
  const [statusInput, setStatusInput] = useState<"active" | "inactive" | "">(
    "",
  );

  // Applied state — triggers the API fetch
  const [appliedSearch, setAppliedSearch] = useState<string | undefined>(
    undefined,
  );
  const [appliedStatus, setAppliedStatus] = useState<
    "active" | "inactive" | ""
  >("");
  const [offset, setOffset] = useState(0);

  const [showCreate, setShowCreate] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

  // PLP-FIX-4 Issue 7b: checklist deep-link /customers?add=1 opens the modal.
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    if (searchParams.get("add") === "1") {
      setShowCreate(true);
    }
  }, [searchParams]);

  // Clear the param on modal close so refresh/back doesn't re-pop.
  function handleCloseCreate() {
    setShowCreate(false);
    if (searchParams.get("add") === "1") {
      router.replace("/customers");
    }
  }

  const { data, isLoading, isError, refetch } = useCustomers({
    offset,
    limit: LIST_PAGE_SIZE,
    search: appliedSearch,
    status: appliedStatus || undefined,
  });

  const customers = useMemo(() => data?.items ?? [], [data]);
  const total = data?.total ?? 0;

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

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: customers,
    columns,
    state: { sorting, columnSizing },
    onSortingChange: setSorting,
    onColumnSizingChange: setColumnSizing,
    columnResizeMode: "onChange",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return <LoadingState type="inline" label="Loading customers..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load customers"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (customers.length === 0 && offset === 0 && !hasActiveFilters) {
    return (
      <>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-semibold text-neutral-900">
              Customers
            </h1>
            <RoleGate permission="customers.create">
              <button
                onClick={() => setShowCreate(true)}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
                data-testid="add-customer-btn"
              >
                + Add Customer
              </button>
            </RoleGate>
          </div>
          <EmptyState
            type="no-data"
            title="No customers yet"
            description="Customers will appear here once added."
          />
        </div>
        <CreateCustomerModal open={showCreate} onClose={handleCloseCreate} />
      </>
    );
  }

  return (
    <>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-neutral-900">Customers</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-neutral-500">
              {total} result{total !== 1 ? "s" : ""}
            </span>
            <RoleGate permission="customers.create">
              <button
                onClick={() => setShowCreate(true)}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
                data-testid="add-customer-btn"
              >
                + Add Customer
              </button>
            </RoleGate>
          </div>
        </div>

        {/* Filter bar — UI-FIX-1C */}
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-neutral-500 font-medium">
              Search
            </label>
            <input
              type="text"
              placeholder="Search by name, email, phone…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="w-72 px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
              aria-label="Search customers"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-neutral-500 font-medium">
              Status
            </label>
            <select
              value={statusInput}
              onChange={(e) =>
                setStatusInput(e.target.value as "active" | "inactive" | "")
              }
              className="px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400 bg-white"
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
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
              data-testid="customer-search-btn"
            >
              Search
            </button>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleClear}
                className="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
                data-testid="customer-clear-btn"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {customers.length === 0 ? (
          <EmptyState
            type="no-results"
            title="No customers match your search"
            description="Try a different search term or clear the filters."
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
      </div>

      <CreateCustomerModal open={showCreate} onClose={handleCloseCreate} />
    </>
  );
}
