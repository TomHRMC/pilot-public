/**
 * JobDetailPanel — Slide-in side panel on job block click
 *
 * Location: apps/web/src/features/dispatch-board/components/JobDetailPanel.tsx
 *
 * Composes JobProfitabilityCard + ETCDrillDown + TimeEntryList.
 * Slide-in panel at /schedule route (not a separate route).
 * Preserves grid context while showing detail.
 *
 * Per batch-fe-b4-design.md §A.2.4
 */

"use client";

import React from "react";
import { useJobDetail, useProjectedMargin } from "../hooks/useJobDetail";
import { JobProfitabilityCard } from "./JobProfitabilityCard";

interface JobDetailPanelProps {
  jobId: string;
  onClose: () => void;
}

function StatusPill({ status }: { status: string }) {
  const classMap: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600",
    scheduled: "bg-brand-50 text-brand-600",
    in_progress: "bg-alert-50 text-alert-600",
    completed: "bg-margin-50 text-margin-600",
    cancelled: "bg-fault-50 text-fault-600",
  };
  const cls = classMap[status] ?? "bg-neutral-100 text-neutral-600";
  const labelMap: Record<string, string> = {
    draft: "Draft",
    scheduled: "Scheduled",
    in_progress: "In Progress",
    completed: "Completed",
    cancelled: "Cancelled",
  };
  const label =
    labelMap[status] ??
    status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, " ");

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium ${cls}`}
    >
      {label}
    </span>
  );
}

/**
 * JobDetailPanel
 *
 * Renders a right-side slide-in panel with full job info.
 * Composes profitability card, time entries, and ETC breakdown.
 */
export function JobDetailPanel({ jobId, onClose }: JobDetailPanelProps) {
  const { data: job, isLoading, isError } = useJobDetail(jobId);
  const { data: margin } = useProjectedMargin(jobId);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <h2 className="text-h2 font-medium text-neutral-900">Job Details</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded-sm"
            aria-label="Close job detail"
          >
            ×
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-body text-neutral-400">Loading…</div>
        </div>
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <h2 className="text-h2 font-medium text-neutral-900">Job Details</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded-sm"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-body text-fault-600">
            Failed to load job details.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full"
      role="region"
      aria-label={`Job detail: ${job.title}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-neutral-200">
        <div className="min-w-0 flex-1">
          <h2 className="text-h2 font-medium text-neutral-900 truncate">
            {job.title}
          </h2>
          <p className="text-body text-neutral-600 truncate mt-0.5">
            {job.customer_name}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-2 flex-shrink-0 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded-sm"
          aria-label="Close job detail panel"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      {/* Body — scrollable */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Status + meta */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusPill status={job.status} />
            <span className="text-caption text-neutral-400 capitalize">
              {job.job_type}
            </span>
            <span className="text-caption text-neutral-400 capitalize">
              {job.priority}
            </span>
          </div>

          <p className="text-body text-neutral-600">{job.site_address}</p>

          {job.scheduled_start_at && job.scheduled_end_at && (
            <p className="text-body text-neutral-600">
              {new Date(job.scheduled_start_at).toLocaleString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
              {" – "}
              {new Date(job.scheduled_end_at).toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
              })}
            </p>
          )}

          {job.tech_name && (
            <p className="text-body text-neutral-600">
              Assigned to:{" "}
              <span className="font-medium text-neutral-900">
                {job.tech_name}
              </span>
            </p>
          )}
        </div>

        {/* Profitability card */}
        {margin && (
          <JobProfitabilityCard
            projectedMargin={margin}
            quoteLines={job.quote_lines ?? []}
          />
        )}

        {/* Time entries */}
        {job.time_entries && job.time_entries.length > 0 && (
          <div>
            <h3 className="text-h3 font-medium text-neutral-900 mb-2">
              Time Entries
            </h3>
            <div className="space-y-2">
              {job.time_entries.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between py-2 border-b border-neutral-100"
                >
                  <div>
                    <p className="text-body text-neutral-900">
                      {entry.tech_name}
                    </p>
                    <p className="text-caption text-neutral-400">
                      {new Date(entry.clock_in_at).toLocaleTimeString("en-US", {
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                      {entry.clock_out_at
                        ? ` – ${new Date(entry.clock_out_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`
                        : " – In progress"}
                    </p>
                  </div>
                  <span className="text-body font-medium text-neutral-900 tabular-nums">
                    {entry.hours_worked.toFixed(1)}h
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
