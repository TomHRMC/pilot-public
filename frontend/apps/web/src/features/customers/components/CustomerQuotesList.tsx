/**
 * CustomerQuotesList — customer-scoped quotes list
 *
 * Location: apps/web/src/features/customers/components/CustomerQuotesList.tsx
 *
 * UI-FIX-2D: Rewritten from placeholder to real data.
 * - Uses useQuotes({ customer_id }) to lock results to this customer's UUID
 * - Customer search input is intentionally HIDDEN (redundant on customer detail page)
 * - All other filters (title search, status, date range) are visible and functional
 * - PilotPaginator preserved for pagination
 * - "+ New Quote" pre-seeded with ?customer_id= query param
 * Added client-side sort on Title, Status, Total, Created columns.
 */

"use client";

import React, { useState, useMemo } from "react";
import { useQuotes } from "../../quotes/hooks/useQuotes";
import type { QuoteListItem } from "../../quotes/hooks/useQuotes";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LoadingState, ErrorState, EmptyState } from "@pilot/ui";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

// ── Sort helpers ──────────────────────────────────────────────────────────────

type QuoteSortField =
  | "quote_number"
  | "title"
  | "status_code"
  | "total_cents"
  | "created_at";
type SortDir = "asc" | "desc";

function SortIcon({
  field,
  sortField,
  sortDir,
}: {
  field: QuoteSortField;
  sortField: QuoteSortField;
  sortDir: SortDir;
}) {
  if (sortField !== field)
    return <span className="ml-1 text-neutral-300">↕</span>;
  return (
    <span className="ml-1 text-brand-600">{sortDir === "asc" ? "↑" : "↓"}</span>
  );
}

function sortQuotes(
  quotes: QuoteListItem[],
  field: QuoteSortField,
  dir: SortDir,
): QuoteListItem[] {
  return [...quotes].sort((a, b) => {
    let cmp = 0;
    switch (field) {
      case "quote_number":
        cmp = (a.quote_number ?? "").localeCompare(b.quote_number ?? "");
        break;
      case "title":
        cmp = (a.title ?? "").localeCompare(b.title ?? "");
        break;
      case "status_code":
        cmp = (a.status_code ?? "").localeCompare(b.status_code ?? "");
        break;
      case "total_cents":
        cmp = (a.total_cents ?? 0) - (b.total_cents ?? 0);
        break;
      case "created_at":
        cmp = (a.created_at ?? "").localeCompare(b.created_at ?? "");
        break;
    }
    return dir === "asc" ? cmp : -cmp;
  });
}

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Pending Approval", value: "pending_approval" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Sent", value: "sent" },
  { label: "Accepted", value: "accepted" },
  { label: "Converted", value: "converted" },
  { label: "Rejected", value: "rejected" },
  { label: "Expired", value: "expired" },
  { label: "Void", value: "void" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  pending_approval: "bg-yellow-100 text-yellow-800",
  pending: "bg-blue-100 text-blue-700",
  approved: "bg-brand-100 text-brand-700",
  sent: "bg-blue-100 text-blue-700",
  accepted: "bg-margin-100 text-margin-700",
  converted: "bg-margin-100 text-margin-700",
  rejected: "bg-fault-100 text-fault-700",
  expired: "bg-neutral-100 text-neutral-500",
  void: "bg-neutral-100 text-neutral-400",
};

function formatCents(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}

function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  return new Date(isoDate).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export interface CustomerQuotesListProps {
  customerId: string;
}

export function CustomerQuotesList({ customerId }: CustomerQuotesListProps) {
  // Pending filter state
  const [pendingStatus, setPendingStatus] = useState("");
  const [pendingTitle, setPendingTitle] = useState("");
  const [pendingDateFrom, setPendingDateFrom] = useState("");
  const [pendingDateTo, setPendingDateTo] = useState("");

  // Applied filter state — triggers API fetch
  const [appliedStatus, setAppliedStatus] = useState("");
  const [appliedTitle, setAppliedTitle] = useState("");
  const [appliedDateFrom, setAppliedDateFrom] = useState("");
  const [appliedDateTo, setAppliedDateTo] = useState("");
  const [offset, setOffset] = useState(0);

  // Client-side sort state
  const [sortField, setSortField] = useState<QuoteSortField>("quote_number");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function handleSort(field: QuoteSortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const { data, isLoading, isError } = useQuotes({
    customer_id: customerId,
    status: appliedStatus || undefined,
    title_search: appliedTitle || undefined,
    date_from: appliedDateFrom || undefined,
    date_to: appliedDateTo || undefined,
    offset,
    limit: LIST_PAGE_SIZE,
  });

  const total = data?.total ?? 0;
  const quotes = useMemo(
    () => sortQuotes(data?.items ?? [], sortField, sortDir),
    [data?.items, sortField, sortDir],
  );

  function handleSearch() {
    setAppliedStatus(pendingStatus);
    setAppliedTitle(pendingTitle);
    setAppliedDateFrom(pendingDateFrom);
    setAppliedDateTo(pendingDateTo);
    setOffset(0);
  }

  function handleClear() {
    setPendingStatus("");
    setPendingTitle("");
    setPendingDateFrom("");
    setPendingDateTo("");
    setAppliedStatus("");
    setAppliedTitle("");
    setAppliedDateFrom("");
    setAppliedDateTo("");
    setOffset(0);
  }

  const hasActiveFilters =
    !!appliedStatus || !!appliedTitle || !!appliedDateFrom || !!appliedDateTo;

  if (isLoading) {
    return (
      <div className="p-4">
        <LoadingState type="inline" label="Loading quotes..." />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4">
        <ErrorState
          type="server"
          title="Could not load quotes"
          description="Check your connection and try again."
        />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Filter bar — Customer search input intentionally omitted */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Title</label>
          <input
            type="text"
            placeholder="Search by title..."
            value={pendingTitle}
            onChange={(e) => setPendingTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-48 px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Search quotes by title"
            data-testid="customer-quotes-title-search"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Status</label>
          <select
            value={pendingStatus}
            onChange={(e) => setPendingStatus(e.target.value)}
            className="px-3 py-2 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            aria-label="Filter by status"
            data-testid="customer-quotes-status-select"
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
            Created From
          </label>
          <input
            type="date"
            value={pendingDateFrom}
            onChange={(e) => setPendingDateFrom(e.target.value)}
            className="px-2 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Quote created date from"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Created To
          </label>
          <input
            type="date"
            value={pendingDateTo}
            onChange={(e) => setPendingDateTo(e.target.value)}
            className="px-2 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Quote created date to"
          />
        </div>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
            data-testid="customer-quotes-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              aria-label="Clear quote filters"
              data-testid="customer-quotes-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
        <a
          href={`/quotes/new?customer_id=${customerId}`}
          className="ml-auto flex items-center gap-1 px-3 py-2 text-sm font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded-md hover:bg-brand-100 transition-colors"
          data-testid="customer-quotes-new-btn"
        >
          <span aria-hidden="true">+</span>
          New Quote
        </a>
      </div>

      {/* Quotes table — Customer column omitted (redundant on customer detail page) */}
      {quotes.length === 0 ? (
        <EmptyState
          type={hasActiveFilters ? "no-results" : "no-data"}
          title={
            hasActiveFilters ? "No quotes match your filters" : "No quotes yet"
          }
          description={
            hasActiveFilters
              ? "Try adjusting your filters."
              : "No quotes for this customer yet."
          }
        />
      ) : (
        <table className="w-full text-sm" data-testid="customer-quotes-table">
          <thead>
            <tr className="border-b border-neutral-200 text-neutral-500 text-left">
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("quote_number")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-quotes-number"
                >
                  Quote #{" "}
                  <SortIcon
                    field="quote_number"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("title")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-quotes-title"
                >
                  Title{" "}
                  <SortIcon
                    field="title"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("status_code")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-quotes-status"
                >
                  Status{" "}
                  <SortIcon
                    field="status_code"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("total_cents")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-quotes-total"
                >
                  Total{" "}
                  <SortIcon
                    field="total_cents"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              <th className="pb-2 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("created_at")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-quotes-created"
                >
                  Created{" "}
                  <SortIcon
                    field="created_at"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {quotes.map((quote) => (
              <tr
                key={quote.id}
                className="border-b border-neutral-50 hover:bg-neutral-50"
              >
                <td className="py-2 pr-4">
                  <a
                    href={`/quotes/${quote.id}`}
                    className="text-brand-600 hover:underline font-medium"
                  >
                    {quote.quote_number ?? quote.id.slice(0, 8)}
                  </a>
                </td>
                <td className="py-2 pr-4 text-neutral-700">
                  {quote.title ?? "—"}
                </td>
                <td className="py-2 pr-4">
                  {quote.status_code ? (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[quote.status_code] ?? "bg-neutral-100 text-neutral-700"}`}
                    >
                      {quote.status_code.replace(/_/g, " ")}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="py-2 pr-4 text-neutral-900 tabular-nums">
                  {formatCents(quote.total_cents)}
                </td>
                <td className="py-2 text-neutral-600">
                  {formatDate(quote.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <PilotPaginator
        total={total}
        limit={LIST_PAGE_SIZE}
        offset={offset}
        onPageChange={setOffset}
      />
    </div>
  );
}
