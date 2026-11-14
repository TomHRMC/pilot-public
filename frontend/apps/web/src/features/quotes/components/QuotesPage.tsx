"use client";

/**
 * QuotesPage — server-side paginated quotes list with filter bar
 *
 * Location: apps/web/src/features/quotes/components/QuotesPage.tsx
 *
 * UI-FIX-1C: Replaced status pills with <select> dropdown.
 * Added customer search, title search, date from/to with explicit Search/Clear.
 * Replaced Load More with PilotPaginator.
 * FE-B28: TanStack Table v8 (preserved).
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
import { useQuotes } from "../hooks/useQuotes";
import { useConvertQuote } from "../hooks/useConvertQuote";
import type { QuoteListItem } from "../hooks/useQuotes";
import { PilotTable } from "../../../components/PilotTable";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Pending Approval", value: "pending_approval" },
  { label: "Sent", value: "sent" },
  { label: "Accepted", value: "accepted" },
  { label: "Expired", value: "expired" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  pending_approval: "bg-alert-100 text-alert-700",
  sent: "bg-brand-100 text-brand-700",
  accepted: "bg-margin-100 text-margin-700",
  approved: "bg-margin-100 text-margin-700",
  converted: "bg-neutral-100 text-neutral-500",
  expired: "bg-neutral-100 text-neutral-500",
};

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function QuotesPage() {
  return (
    <RoleGate permission="quotes.view">
      <QuotesPageContent />
    </RoleGate>
  );
}

// ---------------------------------------------------------------------------
// Row convert button (isolated so it has its own mutation instance per quoteId)
// ---------------------------------------------------------------------------
function ConvertToJobButton({ quoteId }: { quoteId: string }) {
  const { mutate, isPending } = useConvertQuote(quoteId);
  return (
    <button
      onClick={() => mutate()}
      disabled={isPending}
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors disabled:opacity-50"
    >
      {isPending ? "Converting…" : "Convert to Job"}
    </button>
  );
}

// Column helper defined outside component for stability
const columnHelper = createColumnHelper<QuoteListItem>();

// ---------------------------------------------------------------------------
// Main content
// ---------------------------------------------------------------------------
function QuotesPageContent() {
  const router = useRouter();

  // Filter input state (not yet applied)
  const [statusInput, setStatusInput] = useState("");
  const [customerSearchInput, setCustomerSearchInput] = useState("");
  const [titleSearchInput, setTitleSearchInput] = useState("");
  const [dateFromInput, setDateFromInput] = useState("");
  const [dateToInput, setDateToInput] = useState("");

  // Applied state — triggers API fetch
  const [appliedStatus, setAppliedStatus] = useState<string | undefined>(
    undefined,
  );
  const [appliedCustomerSearch, setAppliedCustomerSearch] = useState<
    string | undefined
  >(undefined);
  const [appliedTitleSearch, setAppliedTitleSearch] = useState<
    string | undefined
  >(undefined);
  const [appliedDateFrom, setAppliedDateFrom] = useState<string | undefined>(
    undefined,
  );
  const [appliedDateTo, setAppliedDateTo] = useState<string | undefined>(
    undefined,
  );
  const [offset, setOffset] = useState(0);

  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

  const { data, isLoading, isError, refetch } = useQuotes({
    offset,
    limit: LIST_PAGE_SIZE,
    status: appliedStatus,
    customer_search: appliedCustomerSearch,
    title_search: appliedTitleSearch,
    date_from: appliedDateFrom,
    date_to: appliedDateTo,
  });

  const quotes: QuoteListItem[] = useMemo(() => data?.items ?? [], [data]);
  const total = data?.total ?? 0;

  function handleSearch() {
    setOffset(0);
    setAppliedStatus(statusInput || undefined);
    setAppliedCustomerSearch(customerSearchInput.trim() || undefined);
    setAppliedTitleSearch(titleSearchInput.trim() || undefined);
    setAppliedDateFrom(dateFromInput || undefined);
    setAppliedDateTo(dateToInput || undefined);
  }

  function handleClear() {
    setStatusInput("");
    setCustomerSearchInput("");
    setTitleSearchInput("");
    setDateFromInput("");
    setDateToInput("");
    setOffset(0);
    setAppliedStatus(undefined);
    setAppliedCustomerSearch(undefined);
    setAppliedTitleSearch(undefined);
    setAppliedDateFrom(undefined);
    setAppliedDateTo(undefined);
  }

  const hasActiveFilters =
    !!appliedStatus ||
    !!appliedCustomerSearch ||
    !!appliedTitleSearch ||
    !!appliedDateFrom ||
    !!appliedDateTo;

  const columns = useMemo(
    () => [
      columnHelper.accessor("quote_number", {
        header: "Quote #",
        size: 130,
        minSize: 90,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => {
          const q = info.row.original;
          return (
            <a
              href={`/quotes/${q.id}`}
              className="text-brand-600 hover:underline font-medium text-sm whitespace-nowrap"
            >
              {q.quote_number ?? `${q.id.slice(0, 8)}…`}
            </a>
          );
        },
      }),
      columnHelper.accessor("title", {
        header: "Title",
        size: 180,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-neutral-700 text-sm line-clamp-2">
            {info.getValue() ?? (
              <span className="text-neutral-400 italic">Untitled</span>
            )}
          </span>
        ),
      }),
      columnHelper.accessor("status_code", {
        header: "Status",
        size: 140,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => {
          const q = info.row.original;
          return q.status_code ? (
            <span
              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize whitespace-nowrap ${STATUS_COLORS[q.status_code] ?? "bg-neutral-100 text-neutral-600"}`}
            >
              {q.status_code.replace(/_/g, " ")}
            </span>
          ) : (
            <span className="text-neutral-400 font-mono text-xs whitespace-nowrap">
              {q.status_id.slice(0, 8)}…
            </span>
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
          const q = info.row.original;
          return (
            <span className="text-neutral-700 line-clamp-2">
              {q.customer_name ?? (
                <span className="text-neutral-400 font-mono text-xs">
                  {q.customer_id.slice(0, 8)}…
                </span>
              )}
            </span>
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
          <span className="text-neutral-700 font-medium whitespace-nowrap tabular-nums text-right block">
            {formatCents(info.getValue())}
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
          const q = info.row.original;
          return (
            <div className="flex items-center justify-start gap-2">
              {q.status_code === "draft" && (
                <a
                  href={`/quotes/${q.id}`}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
                >
                  Edit
                </a>
              )}
              {q.status_code === "pending_approval" && (
                <a
                  href={`/quotes/${q.id}/approve`}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
                >
                  Review
                </a>
              )}
              {q.status_code === "approved" && (
                <RoleGate permission="quotes.edit">
                  <a
                    href={`/quotes/${q.id}`}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
                  >
                    Send to Customer
                  </a>
                </RoleGate>
              )}
              {q.status_code === "accepted" && (
                <RoleGate permission="quotes.edit">
                  <ConvertToJobButton quoteId={q.id} />
                </RoleGate>
              )}
            </div>
          );
        },
      }),
    ],
    [],
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: quotes,
    columns,
    state: { sorting, columnSizing },
    onSortingChange: setSorting,
    onColumnSizingChange: setColumnSizing,
    columnResizeMode: "onChange",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return <LoadingState type="inline" label="Loading quotes..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load quotes"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (quotes.length === 0 && offset === 0 && !hasActiveFilters) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-neutral-900">Quotes</h1>
          <RoleGate permission="quotes.create">
            <button
              onClick={() => router.push("/quotes/new")}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
            >
              + New Quote
            </button>
          </RoleGate>
        </div>
        <EmptyState
          type="no-data"
          title="No quotes yet"
          description="Quotes will appear here once created."
        />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Quotes</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-neutral-500">
            {total} result{total !== 1 ? "s" : ""}
          </span>
          <RoleGate permission="quotes.create">
            <button
              onClick={() => router.push("/quotes/new")}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
            >
              + New Quote
            </button>
          </RoleGate>
        </div>
      </div>

      {/* Filter bar — UI-FIX-1C */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        {/* Status dropdown (replaces pills) */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Status</label>
          <select
            value={statusInput}
            onChange={(e) => setStatusInput(e.target.value)}
            className="px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400 bg-white"
            aria-label="Filter by status"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Customer
          </label>
          <input
            type="text"
            placeholder="Customer name…"
            value={customerSearchInput}
            onChange={(e) => setCustomerSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-48 px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
            aria-label="Search by customer name"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Title</label>
          <input
            type="text"
            placeholder="Quote title…"
            value={titleSearchInput}
            onChange={(e) => setTitleSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-48 px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
            aria-label="Search by quote title"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Date From
          </label>
          <input
            type="date"
            value={dateFromInput}
            onChange={(e) => setDateFromInput(e.target.value)}
            className="px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
            aria-label="Quote created date from"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Date To
          </label>
          <input
            type="date"
            value={dateToInput}
            onChange={(e) => setDateToInput(e.target.value)}
            className="px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
            aria-label="Quote created date to"
          />
        </div>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
            data-testid="quotes-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              data-testid="quotes-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {quotes.length === 0 ? (
        <EmptyState
          type="no-results"
          title="No quotes found"
          description={
            appliedStatus
              ? `No ${appliedStatus.replace(/_/g, " ")} quotes match your filters.`
              : "No quotes match your filters."
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
    </div>
  );
}
