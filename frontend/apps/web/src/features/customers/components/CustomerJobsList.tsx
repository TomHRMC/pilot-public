/**
 * CustomerJobsList — customer-scoped jobs list
 *
 * Location: apps/web/src/features/customers/components/CustomerJobsList.tsx
 *
 * UI-FIX-2D: Rewritten from placeholder to real data.
 * - Uses useJobs({ customer_id }) to lock results to this customer's UUID
 * - Customer search input is intentionally HIDDEN (redundant on customer detail page)
 * - All other filters (status, date range) are visible and functional
 * - PilotPaginator preserved for pagination
 * - PLP-FIX-2: "+ New Job" opens the existing JobFormModal with the customer
 *   preselected (prefilledCustomerId) instead of routing to a non-existent
 *   /jobs/new page (Issue 3 fix).
 * JOB-UI-B1: Added Title column (between Job # and Status) + client-side sort on
 *   Job #, Title, Status, and Scheduled columns.
 */

"use client";

import React, { useState, useMemo } from "react";
import { useJobs } from "../../jobs/hooks/useJobs";
import type { JobListItem } from "../../jobs/hooks/useJobs";
import { PilotPaginator } from "../../../components/PilotPaginator";
import { LoadingState, ErrorState, EmptyState, RoleGate } from "@pilot/ui";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";
import { JobFormModal } from "../../jobs/components/JobFormModal";

// ── Sort types ────────────────────────────────────────────────────────────────

type SortField = "job_number" | "title" | "status_code" | "scheduled_start_at";
type SortDir = "asc" | "desc";

function SortIcon({
  field,
  sortField,
  sortDir,
}: {
  field: SortField;
  sortField: SortField;
  sortDir: SortDir;
}) {
  if (sortField !== field)
    return <span className="ml-1 text-neutral-300">↕</span>;
  return (
    <span className="ml-1 text-brand-600">{sortDir === "asc" ? "↑" : "↓"}</span>
  );
}

function sortJobs(
  jobs: JobListItem[],
  field: SortField,
  dir: SortDir,
): JobListItem[] {
  return [...jobs].sort((a, b) => {
    let aVal: string = "";
    let bVal: string = "";
    switch (field) {
      case "job_number":
        aVal = a.job_number ?? "";
        bVal = b.job_number ?? "";
        break;
      case "title":
        aVal = a.title ?? "";
        bVal = b.title ?? "";
        break;
      case "status_code":
        aVal = a.status_code ?? "";
        bVal = b.status_code ?? "";
        break;
      case "scheduled_start_at":
        aVal = a.scheduled_start_at ?? "";
        bVal = b.scheduled_start_at ?? "";
        break;
    }
    const cmp = aVal.localeCompare(bVal);
    return dir === "asc" ? cmp : -cmp;
  });
}

const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Scheduled", value: "scheduled" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  scheduled: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-700",
  invoice_pending: "bg-purple-100 text-purple-700",
  cancelled: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  in_progress: "In Progress",
  completed: "Completed",
  invoice_pending: "Invoice Pending",
  cancelled: "Cancelled",
};

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

export interface CustomerJobsListProps {
  customerId: string;
}

export function CustomerJobsList({ customerId }: CustomerJobsListProps) {
  // PLP-FIX-2: modal state for the "New Job" JobFormModal
  const [addJobOpen, setAddJobOpen] = useState(false);

  // Pending (not yet applied) filter state
  const [pendingStatus, setPendingStatus] = useState("");
  const [pendingFrom, setPendingFrom] = useState("");
  const [pendingTo, setPendingTo] = useState("");

  // Applied filter state — triggers API fetch
  const [appliedStatus, setAppliedStatus] = useState("");
  const [appliedFrom, setAppliedFrom] = useState("");
  const [appliedTo, setAppliedTo] = useState("");
  const [offset, setOffset] = useState(0);

  // JOB-UI-B1: client-side sort state
  const [sortField, setSortField] = useState<SortField>("scheduled_start_at");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const { data, isLoading, isError } = useJobs({
    customer_id: customerId, // ← locked to this customer UUID; no customer_search input shown
    status: appliedStatus || undefined,
    scheduled_from: appliedFrom || undefined,
    scheduled_to: appliedTo || undefined,
    offset,
    limit: LIST_PAGE_SIZE,
  });

  const total = data?.total ?? 0;

  // JOB-UI-B1: apply client-side sort after API response
  const jobs = useMemo(
    () => sortJobs(data?.items ?? [], sortField, sortDir),
    [data?.items, sortField, sortDir],
  );

  function handleSearch() {
    setAppliedStatus(pendingStatus);
    setAppliedFrom(pendingFrom);
    setAppliedTo(pendingTo);
    setOffset(0);
  }

  function handleClear() {
    setPendingStatus("");
    setPendingFrom("");
    setPendingTo("");
    setAppliedStatus("");
    setAppliedFrom("");
    setAppliedTo("");
    setOffset(0);
  }

  const hasActiveFilters = !!appliedStatus || !!appliedFrom || !!appliedTo;

  if (isLoading) {
    return (
      <div className="p-4">
        <LoadingState type="inline" label="Loading jobs..." />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4">
        <ErrorState
          type="server"
          title="Could not load jobs"
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
          <label className="text-xs text-neutral-500 font-medium">Status</label>
          <select
            value={pendingStatus}
            onChange={(e) => setPendingStatus(e.target.value)}
            className="px-3 py-2 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            aria-label="Filter by status"
            data-testid="customer-jobs-status-select"
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
            Scheduled From
          </label>
          <input
            type="date"
            value={pendingFrom}
            onChange={(e) => setPendingFrom(e.target.value)}
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
            value={pendingTo}
            onChange={(e) => setPendingTo(e.target.value)}
            className="px-2 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Job scheduled date to"
          />
        </div>
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
            data-testid="customer-jobs-search-btn"
          >
            Search
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 text-sm font-medium text-neutral-600 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
              aria-label="Clear job filters"
              data-testid="customer-jobs-clear-btn"
            >
              Clear
            </button>
          )}
        </div>
        <RoleGate permission="jobs.create">
          <button
            type="button"
            onClick={() => setAddJobOpen(true)}
            className="ml-auto flex items-center gap-1 px-3 py-2 text-sm font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded-md hover:bg-brand-100 transition-colors"
            data-testid="customer-jobs-new-btn"
          >
            <span aria-hidden="true">+</span>
            New Job
          </button>
        </RoleGate>
      </div>

      {/* Jobs table — Customer column omitted (redundant on customer detail page) */}
      {jobs.length === 0 ? (
        <EmptyState
          type={hasActiveFilters ? "no-results" : "no-data"}
          title={
            hasActiveFilters ? "No jobs match your filters" : "No jobs yet"
          }
          description={
            hasActiveFilters
              ? "Try adjusting your filters."
              : "No jobs for this customer yet."
          }
        />
      ) : (
        <table className="w-full text-sm" data-testid="customer-jobs-table">
          <thead>
            <tr className="border-b border-neutral-200 text-neutral-500 text-left">
              <th className="pb-2 pr-4 font-medium">
                <button
                  type="button"
                  onClick={() => handleSort("job_number")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-job-number"
                >
                  Job #{" "}
                  <SortIcon
                    field="job_number"
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
                  data-testid="sort-title"
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
                  data-testid="sort-status"
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
                  onClick={() => handleSort("scheduled_start_at")}
                  className="flex items-center hover:text-neutral-700 transition-colors"
                  data-testid="sort-scheduled"
                >
                  Scheduled{" "}
                  <SortIcon
                    field="scheduled_start_at"
                    sortField={sortField}
                    sortDir={sortDir}
                  />
                </button>
              </th>
              <th className="pb-2 font-medium">Duration</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr
                key={job.id}
                className="border-b border-neutral-50 hover:bg-neutral-50"
              >
                <td className="py-2 pr-4">
                  <a
                    href={`/jobs/${job.id}`}
                    className="text-brand-600 hover:underline font-medium"
                  >
                    {job.job_number ?? job.id.slice(0, 8)}
                  </a>
                </td>
                {/* JOB-UI-B1: Title column — shows job.title or em-dash when null */}
                <td className="py-2 pr-4 text-neutral-700">
                  {job.title ?? "—"}
                </td>
                <td className="py-2 pr-4">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[job.status_code] ?? "bg-neutral-100 text-neutral-700"}`}
                  >
                    {STATUS_LABELS[job.status_code] ?? job.status_code}
                  </span>
                </td>
                <td className="py-2 pr-4 text-neutral-600">
                  {formatScheduledDate(job.scheduled_start_at)}
                </td>
                <td className="py-2 text-neutral-600">
                  {job.estimated_duration_minutes != null
                    ? `${Math.round((job.estimated_duration_minutes / 60) * 10) / 10}h`
                    : "—"}
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

      {/* PLP-FIX-2: New Job modal — customer preselected; useCreateJob invalidates ["jobs"] */}
      <JobFormModal
        open={addJobOpen}
        onClose={() => setAddJobOpen(false)}
        prefilledCustomerId={customerId}
      />
    </div>
  );
}
