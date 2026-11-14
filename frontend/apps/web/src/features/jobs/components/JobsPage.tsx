/**
 * JobsPage — server-side paginated jobs list with filter bar
 *
 * Location: apps/web/src/features/jobs/components/JobsPage.tsx
 *
 * UI-FIX-1C: Replaced client-side filtering with server-side filters.
 * Status converted from pills to <select> dropdown.
 * Added PilotPaginator — removed client-side filter logic.
 * FE-B31: Recurring badge preserved. Tab navigation preserved.
 * FE-B28: TanStack Table v8 (preserved).
 * JOB-UI-B1: Added Title column (fallback to job_number) + row Edit action.
 */

"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import { LoadingState, ErrorState, EmptyState, RoleGate } from "@pilot/ui";
import { useJobs } from "../hooks/useJobs";
import type { JobListItem } from "../hooks/useJobs";
import { JobFormModal } from "./JobFormModal";
import { PilotTable } from "../../../components/PilotTable";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Scheduled", value: "scheduled" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
];

/** Terminal statuses eligible for invoice conversion */
const TERMINAL_STATUSES = new Set(["completed", "invoice_pending"]);

function formatScheduledDate(isoDate: string | null): string {
  if (!isoDate) return "—";
  return new Date(isoDate).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function StatusBadge({ statusCode }: { statusCode: string }) {
  const colorMap: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-700",
    scheduled: "bg-blue-100 text-blue-700",
    in_progress: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-700",
    invoice_pending: "bg-purple-100 text-purple-700",
    cancelled: "bg-red-100 text-red-700",
  };

  const labelMap: Record<string, string> = {
    draft: "Draft",
    scheduled: "Scheduled",
    in_progress: "In Progress",
    completed: "Completed",
    invoice_pending: "Invoice Pending",
    cancelled: "Cancelled",
  };

  const colorClass = colorMap[statusCode] ?? "bg-neutral-100 text-neutral-700";
  const label = labelMap[statusCode] ?? statusCode;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${colorClass}`}
    >
      {label}
    </span>
  );
}

// Column helper defined outside component for stability
const columnHelper = createColumnHelper<JobListItem>();

/** FE-B31: Job tab navigation items */
const JOB_TABS = [
  { label: "All Jobs", href: "/jobs" },
  { label: "Recurring", href: "/jobs/recurring" },
];

export function JobsPage() {
  const pathname = usePathname();
  const router = useRouter();

  // Filter input state (not yet applied)
  const [statusInput, setStatusInput] = useState("");
  const [customerSearchInput, setCustomerSearchInput] = useState("");
  const [scheduledFromInput, setScheduledFromInput] = useState("");
  const [scheduledToInput, setScheduledToInput] = useState("");

  // Applied state — triggers API fetch
  const [appliedStatus, setAppliedStatus] = useState<string | undefined>(
    undefined,
  );
  const [appliedCustomerSearch, setAppliedCustomerSearch] = useState<
    string | undefined
  >(undefined);
  const [appliedScheduledFrom, setAppliedScheduledFrom] = useState<
    string | undefined
  >(undefined);
  const [appliedScheduledTo, setAppliedScheduledTo] = useState<
    string | undefined
  >(undefined);
  const [offset, setOffset] = useState(0);

  const [addJobOpen, setAddJobOpen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

  const { data, isLoading, isError, error } = useJobs({
    offset,
    limit: LIST_PAGE_SIZE,
    status: appliedStatus,
    customer_search: appliedCustomerSearch,
    scheduled_from: appliedScheduledFrom,
    scheduled_to: appliedScheduledTo,
  });

  const jobs = useMemo(() => data?.items ?? [], [data]);
  const total = data?.total ?? 0;

  function handleSearch() {
    setOffset(0);
    setAppliedStatus(statusInput || undefined);
    setAppliedCustomerSearch(customerSearchInput.trim() || undefined);
    setAppliedScheduledFrom(scheduledFromInput || undefined);
    setAppliedScheduledTo(scheduledToInput || undefined);
  }

  function handleClear() {
    setStatusInput("");
    setCustomerSearchInput("");
    setScheduledFromInput("");
    setScheduledToInput("");
    setOffset(0);
    setAppliedStatus(undefined);
    setAppliedCustomerSearch(undefined);
    setAppliedScheduledFrom(undefined);
    setAppliedScheduledTo(undefined);
  }

  const hasActiveFilters =
    !!appliedStatus ||
    !!appliedCustomerSearch ||
    !!appliedScheduledFrom ||
    !!appliedScheduledTo;

  // Column definitions
  const columns = useMemo(
    () => [
      columnHelper.accessor("customer_name", {
        header: "Customer",
        size: 200,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-sm font-medium text-neutral-900 line-clamp-2 flex items-center gap-1.5">
            {info.getValue()}
            {/* FE-B31: Recurring badge */}
            {info.row.original.recurrence_rule_id != null && (
              <span
                className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700"
                title="Recurring job"
                data-testid="recurring-badge"
              >
                ↻
              </span>
            )}
          </span>
        ),
      }),
      // JOB-UI-B1: Job # column — human-readable identifier (sortable)
      columnHelper.accessor("job_number", {
        id: "job_number",
        header: "Job #",
        size: 130,
        minSize: 80,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span
            className="text-sm font-medium text-neutral-700 whitespace-nowrap"
            data-testid="job-number-cell"
          >
            {info.getValue() ?? "—"}
          </span>
        ),
      }),
      // JOB-UI-B1: Title column — shows job.title only; sortable
      columnHelper.accessor("title", {
        id: "title",
        header: "Title",
        size: 220,
        minSize: 120,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span
            className="text-sm text-neutral-700 line-clamp-2"
            data-testid="job-title-cell"
          >
            {info.getValue() ?? "—"}
          </span>
        ),
      }),
      columnHelper.accessor("status_code", {
        header: "Status",
        size: 140,
        minSize: 100,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => <StatusBadge statusCode={info.getValue() ?? ""} />,
      }),
      columnHelper.accessor("scheduled_start_at", {
        header: "Scheduled",
        size: 180,
        minSize: 120,
        enableResizing: true,
        enableSorting: true,
        cell: (info) => (
          <span className="text-sm text-neutral-600 whitespace-nowrap">
            {formatScheduledDate(info.getValue())}
          </span>
        ),
      }),
      columnHelper.display({
        id: "actions",
        header: "Actions",
        size: 180,
        minSize: 100,
        enableResizing: false,
        enableSorting: false,
        cell: (info) => {
          const job = info.row.original;
          const isTerminal = TERMINAL_STATUSES.has(job.status_code);
          return (
            <div className="flex items-center gap-2 flex-wrap">
              <Link
                href={`/jobs/${job.id}`}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
              >
                View
              </Link>
              {/* JOB-UI-B1: row Edit action → full-page edit */}
              <RoleGate permission="jobs.edit">
                <button
                  type="button"
                  onClick={() => router.push(`/jobs/${job.id}/edit`)}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50 transition-colors"
                  data-testid={`edit-job-row-btn-${job.id}`}
                >
                  Edit
                </button>
              </RoleGate>
              {isTerminal && (
                <RoleGate permission="invoices.create">
                  <Link
                    href={`/invoices/new?job_id=${job.id}`}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
                  >
                    Create Invoice
                  </Link>
                </RoleGate>
              )}
            </div>
          );
        },
      }),
    ],
    [router],
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: jobs,
    columns,
    state: { sorting, columnSizing },
    onSortingChange: setSorting,
    onColumnSizingChange: setColumnSizing,
    columnResizeMode: "onChange",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <LoadingState type="full-page" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <ErrorState
          type="server"
          description={(error as Error)?.message ?? "Failed to load jobs"}
        />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Add Job Modal */}
      <JobFormModal open={addJobOpen} onClose={() => setAddJobOpen(false)} />

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Jobs</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage field jobs, track time and materials, and convert to
            invoices.
          </p>
        </div>
        <RoleGate permission="jobs.create">
          <button
            type="button"
            onClick={() => setAddJobOpen(true)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
            data-testid="add-job-btn"
          >
            <span aria-hidden="true">+</span>
            Add Job
          </button>
        </RoleGate>
      </div>

      {/* FE-B31: Tab navigation — All Jobs | Recurring */}
      <div className="mb-4 border-b border-neutral-200">
        <nav className="flex gap-0" aria-label="Jobs navigation">
          {JOB_TABS.map((tab) => {
            const isActive = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                data-testid={
                  tab.href === "/jobs/recurring"
                    ? "recurring-jobs-tab"
                    : "all-jobs-tab"
                }
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? "border-brand-600 text-brand-700"
                    : "border-transparent text-neutral-600 hover:text-neutral-900 hover:border-neutral-300"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* UI-FIX-1C: Server-side filter bar */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">Status</label>
          <select
            value={statusInput}
            onChange={(e) => setStatusInput(e.target.value)}
            className="px-3 py-2 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            aria-label="Filter by status"
            data-testid="job-status-select"
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
            placeholder="Search by customer..."
            value={customerSearchInput}
            onChange={(e) => setCustomerSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-56 px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Search by customer name"
            data-testid="job-customer-search"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Scheduled From
          </label>
          <input
            type="date"
            value={scheduledFromInput}
            onChange={(e) => setScheduledFromInput(e.target.value)}
            className="px-2 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Job scheduled date from"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-500 font-medium">
            Scheduled To
          </label>
          <input
            type="date"
            value={scheduledToInput}
            onChange={(e) => setScheduledToInput(e.target.value)}
            className="px-2 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Job scheduled date to"
          />
        </div>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
            data-testid="job-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              aria-label="Clear job filters"
              data-testid="job-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      {jobs.length === 0 ? (
        <EmptyState
          type={hasActiveFilters ? "no-results" : "no-data"}
          title={
            hasActiveFilters ? "No jobs match your filters" : "No jobs yet"
          }
          description={
            hasActiveFilters
              ? "Try adjusting your status filter, customer search, or date range."
              : "Jobs will appear here once created from the dispatch board."
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
