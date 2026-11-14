"use client";

/**
 * CommsPage — Cross-customer Communications Summary
 *
 * Location: apps/web/src/features/comms/components/CommsPage.tsx
 *
 * COMMS-UI-B1: Refactored from raw <table> in the route file to a feature
 * component with TanStack Table (sortable columns), a filter bar (customer
 * search + channel pill + date range) driving server-side params, and
 * PilotPaginator (offset/limit).
 *
 * RULE: Uses apiClient via useRecentComms (never raw fetch).
 * RULE: TanStack Query v5 object-form; isPending not isLoading.
 * RULE: React Compiler — no hand-written useMemo/useCallback for render-perf.
 * RULE: Filters drive server-side params (not client-side filtering).
 * RULE: WCAG 2.2 AA — target size ≥24px, non-color-only badges, focus-visible.
 *
 * Preserved testids (E2E + integration specs depend on these):
 *   comms-page, recent-comms-table, comm-row-{id},
 *   "No messages sent yet…" empty text, SMS/Email channel span,
 *   customer Link to /customers/{id}/comms
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { RoleGate } from "@pilot/ui/role-gate";
import { PilotTable } from "../../../components/PilotTable";
import { PilotPaginator } from "../../../components/PilotPaginator";
import {
  useRecentComms,
  COMMS_PAGE_SIZE,
  type CommunicationSummaryItem,
} from "../hooks/useRecentComms";

// ── Column definitions (module-level for stable reference) ──────────────────

const columnHelper = createColumnHelper<CommunicationSummaryItem>();

const columns = [
  columnHelper.accessor("customer_name", {
    header: "Customer",
    enableSorting: true,
    cell: (info) => (
      <Link
        href={`/customers/${info.row.original.customer_id}/comms`}
        className="text-body font-medium text-brand-600 hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  columnHelper.accessor("channel", {
    header: "Channel",
    enableSorting: true,
    cell: (info) => {
      const channel = info.getValue();
      const isSms = channel === "sms";
      return (
        <span
          className={[
            "inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium",
            isSms
              ? "bg-brand-50 text-brand-800"
              : "bg-neutral-100 text-neutral-600",
          ].join(" ")}
        >
          {isSms ? "SMS" : "Email"}
        </span>
      );
    },
  }),
  columnHelper.accessor("direction", {
    header: "Direction",
    enableSorting: true,
    cell: (info) => {
      const direction = info.getValue();
      const isOutbound = direction === "outbound";
      return (
        <span className="inline-flex items-center gap-1 text-caption text-neutral-500">
          {/* Non-color-only: arrow icon paired with text label (WCAG 1.4.1) */}
          <span aria-hidden="true">{isOutbound ? "↑" : "↓"}</span>
          <span className="capitalize">{direction}</span>
        </span>
      );
    },
  }),
  columnHelper.accessor("body", {
    header: "Message",
    enableSorting: false,
    cell: (info) => (
      <p
        className="truncate text-body text-neutral-900"
        title={info.getValue()}
      >
        {info.getValue()}
      </p>
    ),
  }),
  columnHelper.accessor("created_at", {
    header: "Time",
    enableSorting: true,
    cell: (info) => {
      const created = info.getValue();
      return (
        <span className="text-caption text-neutral-600">
          {created ? new Date(created).toLocaleString() : "—"}
        </span>
      );
    },
  }),
];

// ── Component ─────────────────────────────────────────────────────────────────

export function CommsPage() {
  // Pagination state
  const [offset, setOffset] = useState(0);
  const limit = COMMS_PAGE_SIZE;

  // Filter state
  const [customerSearchInput, setCustomerSearchInput] = useState("");
  const [customerSearch, setCustomerSearch] = useState("");
  const [channel, setChannel] = useState<"" | "sms" | "email">("");
  const [sentFrom, setSentFrom] = useState("");
  const [sentTo, setSentTo] = useState("");

  // Sorting state
  const [sorting, setSorting] = useState<SortingState>([]);

  // Debounce customer search (~300ms) — also resets to first page
  // setOffset is identity-stable; this is a legitimate timer side-effect
  useEffect(() => {
    const timer = setTimeout(() => {
      setCustomerSearch(customerSearchInput);
      setOffset(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [customerSearchInput]);

  const { data, isPending, isError, error, refetch } = useRecentComms({
    limit,
    offset,
    customer_search: customerSearch.trim() || undefined,
    channel: channel || undefined,
    sent_from: sentFrom || undefined,
    sent_to: sentTo || undefined,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: items,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <RoleGate permission="communications.view">
      <main className="flex min-h-screen flex-col p-6" data-testid="comms-page">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-h1 font-medium text-neutral-900">
            Communications
          </h1>
          <p className="text-caption text-neutral-400">
            Recent messages across all customers
          </p>
        </div>

        {/* Filter bar — COMMS-UI-B1 */}
        <div className="mb-4 flex flex-wrap items-end gap-3">
          {/* Customer search (debounced) */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="comms-customer-search"
              className="text-xs font-medium text-neutral-500"
            >
              Customer
            </label>
            <input
              id="comms-customer-search"
              type="text"
              placeholder="Search by customer name…"
              value={customerSearchInput}
              onChange={(e) => setCustomerSearchInput(e.target.value)}
              className="w-64 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              data-testid="comms-customer-search"
            />
          </div>

          {/* Channel pill toggle — All · SMS · Email */}
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-neutral-500">
              Channel
            </span>
            <div
              className="inline-flex overflow-hidden rounded-md border border-neutral-200"
              data-testid="comms-channel-filter"
              role="group"
              aria-label="Filter by channel"
            >
              {(["", "sms", "email"] as const).map((ch) => {
                const label =
                  ch === "" ? "All" : ch === "sms" ? "SMS" : "Email";
                const isActive = channel === ch;
                return (
                  <button
                    key={ch}
                    type="button"
                    onClick={() => {
                      setChannel(ch);
                      setOffset(0);
                    }}
                    aria-pressed={isActive}
                    className={[
                      "px-3 py-1.5 text-sm font-medium transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400",
                      isActive
                        ? "bg-brand-600 text-white"
                        : "bg-white text-neutral-600 hover:bg-neutral-50",
                    ].join(" ")}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date range — sent_from / sent_to */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="comms-date-from"
              className="text-xs font-medium text-neutral-500"
            >
              Sent from
            </label>
            <input
              id="comms-date-from"
              type="date"
              value={sentFrom}
              onChange={(e) => {
                setSentFrom(e.target.value);
                setOffset(0);
              }}
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              data-testid="comms-date-from"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label
              htmlFor="comms-date-to"
              className="text-xs font-medium text-neutral-500"
            >
              Sent to
            </label>
            <input
              id="comms-date-to"
              type="date"
              value={sentTo}
              onChange={(e) => {
                setSentTo(e.target.value);
                setOffset(0);
              }}
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              data-testid="comms-date-to"
            />
          </div>
        </div>

        {/* Loading state */}
        {isPending && (
          <LoadingState type="inline" label="Loading communications…" />
        )}

        {/* Error state */}
        {isError && (
          <ErrorState
            type="server"
            title="Failed to load communications"
            description={
              error instanceof Error ? error.message : "Unknown error"
            }
            onRetry={() => void refetch()}
          />
        )}

        {/* Empty state — preserve exact string (E2E depends on it) */}
        {data && items.length === 0 && !isPending && (
          <p className="text-body text-neutral-400">
            No messages sent yet. Visit a customer to send their first message.
          </p>
        )}

        {/* Table + Paginator */}
        {items.length > 0 && (
          <>
            <PilotTable
              table={table}
              tableDataTestId="recent-comms-table"
              getRowDataTestId={(item) => `comm-row-${item.id}`}
            />
            <PilotPaginator
              total={total}
              limit={limit}
              offset={offset}
              onPageChange={setOffset}
            />
          </>
        )}
      </main>
    </RoleGate>
  );
}
