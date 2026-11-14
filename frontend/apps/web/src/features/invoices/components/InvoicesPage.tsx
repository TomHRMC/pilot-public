"use client";

/**
 * InvoicesPage — server-side paginated invoices list with filter bar
 *
 * Location: apps/web/src/features/invoices/components/InvoicesPage.tsx
 *
 * UI-FIX-1C: Added server-side customer_search + issued_from/issued_to filters.
 * Kept existing status pills and Overdue toggle (per design doc).
 * Added PilotPaginator — replaced Load More.
 * Customer search and date pickers now use explicit Search/Clear pattern.
 * FE-B28: TanStack Table v8 (preserved).
 *
 * RBAC: Wrapped in <RoleGate permission="invoices.view"> — tech role sees nothing.
 */

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import { RoleGate } from "@pilot/ui/role-gate";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { useInvoices } from "../hooks/useInvoices";
import type { InvoiceListItem } from "../hooks/useInvoices";
import { InvoiceCreateModal } from "./InvoiceCreateModal";
import { TaxSetupSubFlowModal } from "./TaxSetupSubFlowModal";
import { PilotTable } from "../../../components/PilotTable";
import { PilotPaginator } from "../../../components/PilotPaginator";

const PAGE_SIZE = 50;

/**
 * SD-06: Status filter pills — DB status codes only (confirmed MCP 2026-07-06).
 */
function formatCents(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Draft", value: "draft" },
  { label: "Sent", value: "issued" },
  { label: "Paid", value: "paid" },
  { label: "Void", value: "void" },
  { label: "Write-Off", value: "writeoff" },
] as const;

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  issued: "bg-brand-100 text-brand-700",
  paid: "bg-margin-100 text-margin-700",
  void: "bg-neutral-100 text-neutral-500",
  writeoff: "bg-neutral-100 text-neutral-400",
};

/**
 * SD-06: Derived "overdue" display helper.
 * "Overdue" is NOT a DB status code — it is derived at render time.
 */
export const isOverdue = (invoice: {
  due_at: string | null;
  status_code: string;
}): boolean =>
  invoice.due_at !== null &&
  new Date(invoice.due_at) < new Date() &&
  !["paid", "void", "writeoff"].includes(invoice.status_code);

// UI-FIX-1B: FIX-010b — compute aging bucket from due_at; client-side only
function getAgingBucket(invoice: {
  due_at: string | null;
  status_code: string;
}): string {
  if (!isOverdue(invoice)) return "Current";
  const daysOverdue = Math.floor(
    (Date.now() - new Date(invoice.due_at!).getTime()) / 86_400_000,
  );
  if (daysOverdue <= 60) return "30+";
  if (daysOverdue <= 90) return "60+";
  return "90+";
}

const AGING_BADGE: Record<string, string> = {
  Current: "bg-margin-100 text-margin-700",
  "30+": "bg-alert-100 text-alert-600",
  "60+": "bg-alert-100 text-alert-700",
  "90+": "bg-fault-100 text-fault-700",
};

export function InvoicesPage() {
  return (
    <RoleGate permission="invoices.view">
      <InvoicesPageContent />
    </RoleGate>
  );
}

const columnHelper = createColumnHelper<InvoiceListItem>();

function InvoicesPageContent() {
  const { addNotification } = useNotificationQueue();
  const router = useRouter();

  // Existing status + overdue filters — kept as-is (pills UI)
  const [activeStatus, setActiveStatus] = useState<string | undefined>(
    undefined,
  );
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);
  const [offset, setOffset] = useState(0);

  // UI-FIX-1C: new filter inputs (not yet applied)
  const [customerSearchInput, setCustomerSearchInput] = useState("");
  const [issuedFromInput, setIssuedFromInput] = useState("");
  const [issuedToInput, setIssuedToInput] = useState("");

  // Applied server-side filter values
  const [appliedCustomerSearch, setAppliedCustomerSearch] = useState<
    string | undefined
  >(undefined);
  const [appliedIssuedFrom, setAppliedIssuedFrom] = useState<
    string | undefined
  >(undefined);
  const [appliedIssuedTo, setAppliedIssuedTo] = useState<string | undefined>(
    undefined,
  );

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [taxSetupOpen, setTaxSetupOpen] = useState(false);
  const [taxSetupDetail, setTaxSetupDetail] = useState<string>("");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

  const { data, isLoading, isError, refetch } = useInvoices({
    status: activeStatus,
    limit: PAGE_SIZE,
    offset,
    overdue: showOverdueOnly || undefined,
    customer_search: appliedCustomerSearch,
    issued_from: appliedIssuedFrom,
    issued_to: appliedIssuedTo,
  });

  const handleStatusChange = (status: string | undefined) => {
    setActiveStatus(status);
    setOffset(0);
  };

  const handleOverdueToggle = () => {
    setShowOverdueOnly((prev) => !prev);
    setOffset(0);
  };

  function handleSearch() {
    setOffset(0);
    setAppliedCustomerSearch(customerSearchInput.trim() || undefined);
    setAppliedIssuedFrom(issuedFromInput || undefined);
    setAppliedIssuedTo(issuedToInput || undefined);
  }

  function handleClear() {
    setCustomerSearchInput("");
    setIssuedFromInput("");
    setIssuedToInput("");
    setOffset(0);
    setAppliedCustomerSearch(undefined);
    setAppliedIssuedFrom(undefined);
    setAppliedIssuedTo(undefined);
  }

  const hasActiveFilters =
    !!appliedCustomerSearch || !!appliedIssuedFrom || !!appliedIssuedTo;

  const items = useMemo(() => data?.items ?? [], [data]);
  const total = data?.total ?? 0;

  const columns = useMemo(
    () => [
      columnHelper.accessor("invoice_number", {
        header: "Invoice #",
        size: 140,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => {
          const inv = info.row.original;
          return (
            <a
              href={`/invoices/${inv.id}`}
              className="text-brand-600 hover:underline font-medium whitespace-nowrap"
            >
              {info.getValue()}
            </a>
          );
        },
      }),
      columnHelper.accessor("customer_name", {
        header: "Customer",
        size: 180,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => {
          const inv = info.row.original;
          return (
            <span className="text-neutral-700 text-sm line-clamp-2">
              {inv.customer_name ?? `${inv.customer_id.slice(0, 8)}…`}
            </span>
          );
        },
      }),
      columnHelper.accessor("status_code", {
        header: "Status",
        size: 170,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => {
          const inv = info.row.original;
          return (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span
                className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize whitespace-nowrap ${STATUS_COLORS[inv.status_code] ?? "bg-neutral-100 text-neutral-600"}`}
              >
                {inv.status_code.replace(/_/g, " ")}
              </span>
              {/* SD-06: Derived overdue badge */}
              {isOverdue(inv) && (
                <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-fault-100 text-fault-700 whitespace-nowrap">
                  Overdue
                </span>
              )}
            </div>
          );
        },
      }),
      columnHelper.accessor("total_cents", {
        header: "Total",
        size: 110,
        minSize: 80,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-right text-neutral-900 tabular-nums whitespace-nowrap block">
            {formatCents(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor("issued_at", {
        header: "Issued",
        size: 130,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-neutral-600 whitespace-nowrap">
            {info.getValue()
              ? new Date(info.getValue()!).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })
              : "—"}
          </span>
        ),
      }),
      columnHelper.accessor("due_at", {
        header: "Due",
        size: 130,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-neutral-600 whitespace-nowrap">
            {info.getValue()
              ? new Date(info.getValue()!).toLocaleDateString()
              : "—"}
          </span>
        ),
      }),
      // UI-FIX-1B: FIX-010b — computed Aging column (client-side only)
      columnHelper.display({
        id: "aging",
        header: "Aging",
        size: 90,
        minSize: 70,
        enableResizing: false,
        enableSorting: false,
        cell: (info) => {
          const inv = info.row.original;
          if (["paid", "void", "writeoff"].includes(inv.status_code)) {
            return <span className="text-neutral-400 text-xs">—</span>;
          }
          const bucket = getAgingBucket(inv);
          return (
            <span
              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${AGING_BADGE[bucket]}`}
            >
              {bucket}
            </span>
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

  if (isLoading) {
    return <LoadingState type="inline" label="Loading invoices..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load invoices"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Invoices</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-neutral-500">{total} total</span>
          <RoleGate permission="invoices.create">
            <button
              type="button"
              onClick={() => router.push("/invoices/new")}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
              data-testid="create-invoice-btn"
            >
              <span aria-hidden="true">+</span>
              Create Invoice
            </button>
          </RoleGate>
        </div>
      </div>

      {/* FE-B24: Reworked InvoiceCreateModal */}
      <InvoiceCreateModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onTaxSetupRequired={(detail) => {
          setCreateModalOpen(false);
          setTaxSetupDetail(detail);
          setTaxSetupOpen(true);
        }}
        onSuccess={(invoice) => {
          setCreateModalOpen(false);
          addNotification({
            id: `invoice-created-${invoice.id}`,
            severity: "success",
            title: "Invoice created successfully.",
          });
          void refetch();
        }}
      />

      {/* Tax Setup Sub-Flow Modal */}
      <TaxSetupSubFlowModal
        open={taxSetupOpen}
        detail={taxSetupDetail}
        onClose={() => setTaxSetupOpen(false)}
      />

      {/* Status pills — kept as-is per UI-FIX-1C design decision */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => handleStatusChange(f.value)}
            className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
              activeStatus === f.value
                ? "bg-brand-600 text-white border-brand-600"
                : "bg-white text-neutral-600 border-neutral-200 hover:border-brand-400"
            }`}
          >
            {f.label}
          </button>
        ))}
        {/* SD-06: "Overdue" is a derived display property, not a DB status code */}
        <button
          data-testid="overdue-toggle"
          onClick={handleOverdueToggle}
          className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
            showOverdueOnly
              ? "bg-fault-600 text-white border-fault-600"
              : "bg-white text-fault-600 border-fault-200 hover:border-fault-400"
          }`}
          aria-pressed={showOverdueOnly}
        >
          Overdue Only
        </button>
      </div>

      {/* UI-FIX-1C: server-side customer search + issued date range */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Customer
          </label>
          <input
            type="text"
            placeholder="Search by customer…"
            value={customerSearchInput}
            onChange={(e) => setCustomerSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-56 px-3 py-1.5 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Search invoices by customer name"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Issued From
          </label>
          <input
            type="date"
            value={issuedFromInput}
            onChange={(e) => setIssuedFromInput(e.target.value)}
            className="px-2 py-1.5 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Invoice issued date from"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Issued To
          </label>
          <input
            type="date"
            value={issuedToInput}
            onChange={(e) => setIssuedToInput(e.target.value)}
            className="px-2 py-1.5 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Invoice issued date to"
          />
        </div>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-1.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
            data-testid="invoice-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-1.5 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              aria-label="Clear invoice filters"
              data-testid="invoice-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState
          type="no-results"
          title="No invoices found"
          description={
            activeStatus ? `No ${activeStatus} invoices.` : "No invoices yet."
          }
        />
      ) : (
        <>
          <PilotTable table={table} />
          <PilotPaginator
            total={total}
            limit={PAGE_SIZE}
            offset={offset}
            onPageChange={setOffset}
          />
        </>
      )}
    </div>
  );
}
