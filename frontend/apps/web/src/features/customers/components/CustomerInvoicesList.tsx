/**
 * CustomerInvoicesList — customer-scoped invoices list
 *
 * Location: apps/web/src/features/customers/components/CustomerInvoicesList.tsx
 *
 * UI-FIX-2D: Rewritten from placeholder to real data.
 * - Uses useInvoices({ customer_id }) to lock results to this customer's UUID
 * - Customer search input is intentionally HIDDEN (redundant on customer detail page)
 * - Status pills, Overdue Only toggle, date range pickers, Search/Clear visible
 * - Aging column: computed from due_at (client-side) — same getAgingBucket as InvoicesPage
 * - PilotPaginator preserved for pagination
 * - "+ New Invoice" pre-seeded with ?customer_id= query param
 *
 * IMPORTANT: "overdue" is NOT a DB status code. It is a derived display state.
 * The Overdue Only toggle sends ?overdue=true to API — NOT ?status=overdue.
 *
 * Added client-side sort on Invoice #, Aging, Total, Due Date columns.
 * Status column is NOT sortable (per design decision).
 */

"use client";

import React, { useState, useMemo } from "react";
import { useInvoices } from "../../invoices/hooks/useInvoices";
import type { InvoiceListItem } from "../../invoices/hooks/useInvoices";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LoadingState, ErrorState, EmptyState } from "@pilot/ui";

const PAGE_SIZE = 50;

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

const AGING_BADGE: Record<string, string> = {
  Current: "bg-margin-100 text-margin-700",
  "30+": "bg-alert-100 text-alert-600",
  "60+": "bg-alert-100 text-alert-700",
  "90+": "bg-fault-100 text-fault-700",
};

// ── Sort helpers ──────────────────────────────────────────────────────────────

type InvoiceSortField = "invoice_number" | "aging" | "total_cents" | "due_at";
type SortDir = "asc" | "desc";

/** Numeric sort weight for aging bucket — used for sortable aging column */
const AGING_ORDER: Record<string, number> = {
  Current: 0,
  "30+": 1,
  "60+": 2,
  "90+": 3,
};

function SortIcon({
  field,
  sortField,
  sortDir,
}: {
  field: InvoiceSortField;
  sortField: InvoiceSortField;
  sortDir: SortDir;
}) {
  if (sortField !== field)
    return <span className="ml-1 text-neutral-300">↕</span>;
  return (
    <span className="ml-1 text-brand-600">{sortDir === "asc" ? "↑" : "↓"}</span>
  );
}

/** SD-06: Derived "overdue" display helper — NOT a DB status code. */
function isOverdue(invoice: {
  due_at: string | null;
  status_code: string;
}): boolean {
  return (
    invoice.due_at !== null &&
    new Date(invoice.due_at) < new Date() &&
    !["paid", "void", "writeoff"].includes(invoice.status_code)
  );
}

/** UI-FIX-1B: FIX-010b — compute aging bucket from due_at; client-side only */
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

function sortInvoices(
  items: InvoiceListItem[],
  field: InvoiceSortField,
  dir: SortDir,
): InvoiceListItem[] {
  return [...items].sort((a, b) => {
    let cmp = 0;
    switch (field) {
      case "invoice_number":
        cmp = (a.invoice_number ?? "").localeCompare(b.invoice_number ?? "");
        break;
      case "aging": {
        const aBucket = getAgingBucket(a);
        const bBucket = getAgingBucket(b);
        cmp = (AGING_ORDER[aBucket] ?? 0) - (AGING_ORDER[bBucket] ?? 0);
        break;
      }
      case "total_cents":
        cmp = (a.total_cents ?? 0) - (b.total_cents ?? 0);
        break;
      case "due_at":
        cmp = (a.due_at ?? "").localeCompare(b.due_at ?? "");
        break;
    }
    return dir === "asc" ? cmp : -cmp;
  });
}

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

export interface CustomerInvoicesListProps {
  customerId: string;
}

export function CustomerInvoicesList({
  customerId,
}: CustomerInvoicesListProps) {
  // Status pills + overdue toggle
  const [activeStatus, setActiveStatus] = useState<string | undefined>(
    undefined,
  );
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);
  const [offset, setOffset] = useState(0);

  // Issued date range filter inputs
  const [issuedFromInput, setIssuedFromInput] = useState("");
  const [issuedToInput, setIssuedToInput] = useState("");

  // Applied server-side issued date range
  const [appliedIssuedFrom, setAppliedIssuedFrom] = useState<
    string | undefined
  >(undefined);
  const [appliedIssuedTo, setAppliedIssuedTo] = useState<string | undefined>(
    undefined,
  );

  // Client-side sort state
  const [sortField, setSortField] = useState<InvoiceSortField>("due_at");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  function handleSort(field: InvoiceSortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const { data, isLoading, isError } = useInvoices({
    customer_id: customerId,
    status: activeStatus,
    limit: PAGE_SIZE,
    offset,
    overdue: showOverdueOnly || undefined,
    issued_from: appliedIssuedFrom,
    issued_to: appliedIssuedTo,
  });

  const total = data?.total ?? 0;
  const items = useMemo(
    () => sortInvoices(data?.items ?? [], sortField, sortDir),
    [data?.items, sortField, sortDir],
  );

  function handleStatusChange(status: string | undefined) {
    setActiveStatus(status);
    setOffset(0);
  }

  function handleOverdueToggle() {
    setShowOverdueOnly((prev) => !prev);
    setOffset(0);
  }

  function handleSearch() {
    setAppliedIssuedFrom(issuedFromInput || undefined);
    setAppliedIssuedTo(issuedToInput || undefined);
    setOffset(0);
  }

  function handleClear() {
    setIssuedFromInput("");
    setIssuedToInput("");
    setAppliedIssuedFrom(undefined);
    setAppliedIssuedTo(undefined);
    setOffset(0);
  }

  const hasActiveFilters = !!appliedIssuedFrom || !!appliedIssuedTo;

  if (isLoading) {
    return (
      <div className="p-4">
        <LoadingState type="inline" label="Loading invoices..." />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4">
        <ErrorState
          type="server"
          title="Could not load invoices"
          description="Check your connection and try again."
        />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Status pills — kept as-is from InvoicesPage pattern */}
      <div className="flex flex-wrap items-center gap-2">
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
        {/* SD-06: "Overdue" is derived — NOT a DB status code. Sends ?overdue=true, NOT ?status=overdue */}
        <button
          data-testid="customer-invoices-overdue-toggle"
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

      {/* Issued date range filter — Customer search input intentionally omitted */}
      <div className="flex flex-wrap items-end gap-3">
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
            data-testid="customer-invoices-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-1.5 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              aria-label="Clear invoice filters"
              data-testid="customer-invoices-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
        <a
          href={`/invoices/new?customer_id=${customerId}`}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded-md hover:bg-brand-100 transition-colors"
          data-testid="customer-invoices-new-btn"
        >
          <span aria-hidden="true">+</span>
          New Invoice
        </a>
      </div>

      {/* Invoices table — Customer column omitted (redundant on customer detail page) */}
      {items.length === 0 ? (
        <EmptyState
          type={
            hasActiveFilters || activeStatus || showOverdueOnly
              ? "no-results"
              : "no-data"
          }
          title={
            hasActiveFilters || activeStatus || showOverdueOnly
              ? "No invoices match your filters"
              : "No invoices yet"
          }
          description={
            hasActiveFilters || activeStatus || showOverdueOnly
              ? "Try adjusting your filters."
              : "No invoices for this customer yet."
          }
        />
      ) : (
        <table className="w-full text-sm" data-testid="customer-invoices-table">
          <thead>
            <tr className="border-b border-neutral-200 text-neutral-500 text-left">
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("invoice_number")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-invoices-number"
                >
                  Invoice #{" "}
                  <SortIcon
                    field="invoice_number"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              {/* Status column — NOT sortable per design decision */}
              <th className="pb-2 pr-4 font-medium">Status</th>
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("aging")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-invoices-aging"
                >
                  Aging{" "}
                  <SortIcon
                    field="aging"
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
                  data-testid="sort-invoices-total"
                >
                  Total{" "}
                  <SortIcon
                    field="total_cents"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("due_at")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-invoices-due-date"
                >
                  Due Date{" "}
                  <SortIcon
                    field="due_at"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((inv) => {
              const agingBucket = getAgingBucket(inv);
              const isTerminal = ["paid", "void", "writeoff"].includes(
                inv.status_code,
              );
              return (
                <tr
                  key={inv.id}
                  className="border-b border-neutral-50 hover:bg-neutral-50"
                >
                  <td className="py-2 pr-4">
                    <a
                      href={`/invoices/${inv.id}`}
                      className="text-brand-600 hover:underline font-medium"
                    >
                      {inv.invoice_number}
                    </a>
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[inv.status_code] ?? "bg-neutral-100 text-neutral-600"}`}
                      >
                        {inv.status_code.replace(/_/g, " ")}
                      </span>
                      {/* SD-06: Derived overdue badge */}
                      {isOverdue(inv) && (
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-fault-100 text-fault-700">
                          Overdue
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 pr-4">
                    {isTerminal ? (
                      <span className="text-neutral-400 text-xs">—</span>
                    ) : (
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${AGING_BADGE[agingBucket]}`}
                      >
                        {agingBucket}
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-neutral-900 tabular-nums">
                    {formatCents(inv.total_cents)}
                  </td>
                  <td className="py-2 text-neutral-600">
                    {formatDate(inv.due_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      <PilotPaginator
        total={total}
        limit={PAGE_SIZE}
        offset={offset}
        onPageChange={setOffset}
      />
    </div>
  );
}
