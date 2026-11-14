/**
 * JobPropertiesPanel — Right-side properties inspector panel for a dispatch board job
 *
 * Location: apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx
 *
 * Opens when a job block is clicked on DispatchBoardLanes.
 * Seven sections per batch-mkt-b11-dispatch-react-engr-prompt.md §Task 4:
 *   1. Header (title + status badge + close)
 *   2. Customer & Site
 *   3. Schedule (editable inline — PATCH /api/v1/jobs/{id})
 *   4. Assigned Technicians (editable)
 *   5. Job Status (change action)
 *   6. Notes (editable inline)
 *   7. Actions footer (View Full Job | Create Invoice)
 *
 * Slide-in from right, w-80 (320px) on desktop.
 * Close via × button, Escape key, or clicking outside.
 *
 * Per batch-mkt-b11-dispatch-react-engr-prompt.md §Task 4
 */

"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { DISPATCH_BOARD_QUERY_KEY } from "../hooks/useDispatchBoard";
import type { ScheduledJob } from "./DispatchBoardLanes";
import type { DispatchBoardTech } from "../types-stub";
import { TechAssignmentSection } from "../../jobs/components/TechAssignmentSection";

// ─── Types ────────────────────────────────────────────────────────────────────

interface JobPropertiesPanelProps {
  /** null = panel closed */
  job: ScheduledJob | null;
  onClose: () => void;
  onJobUpdated: (job: ScheduledJob) => void;
  /** Available techs from the dispatch board — used to resolve tech_id → name */
  techs?: DispatchBoardTech[];
}

type JobStatus =
  | "draft"
  | "scheduled"
  | "in_progress"
  | "completed"
  | "cancelled";

// ─── Status helpers ───────────────────────────────────────────────────────────

const STATUS_LABELS: Record<JobStatus, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  in_progress: "In Progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

const STATUS_CLASSES: Record<JobStatus, string> = {
  draft: "bg-neutral-100 text-neutral-600",
  scheduled: "bg-brand-50 text-brand-600",
  in_progress: "bg-alert-50 text-alert-600",
  completed: "bg-margin-50 text-margin-600",
  cancelled: "bg-fault-50 text-fault-600",
};

// ALL_STATUSES — reserved for future status-change dropdown; not yet rendered.
// Suppressed: this array is referenced indirectly through STATUS_LABELS/STATUS_CLASSES
// but kept to enumerate valid transitions for future use.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const ALL_STATUSES: JobStatus[] = [
  "draft",
  "scheduled",
  "in_progress",
  "completed",
  "cancelled",
];

// ─── Sub-components ───────────────────────────────────────────────────────────

// ─── DISPATCH-B3: Classification chip sub-components ─────────────────────────

/**
 * Read-only classification chip row displayed in Section 2 (Customer & Site).
 * Shows Priority / Customer Type / Site Type / Job Type from CLASS-B1 enriched data.
 * All display-only — no mutations (job editing lives on /jobs/:id).
 */
function ClassificationChips({ job }: { job: ScheduledJob }) {
  const typedJob = job as unknown as {
    priority?: string | null;
    customer_type?: string | null;
    site_type?: string | null;
    job_type_label?: string | null;
  };

  const priorityCls =
    typedJob.priority === "emergency"
      ? "bg-fault-100 text-fault-700"
      : typedJob.priority === "urgent"
        ? "bg-alert-100 text-alert-700"
        : "bg-neutral-100 text-neutral-600";

  const priorityLabel = typedJob.priority
    ? typedJob.priority.charAt(0).toUpperCase() + typedJob.priority.slice(1)
    : null;

  const customerTypeLabel =
    typedJob.customer_type === "person"
      ? "Person"
      : typedJob.customer_type === "company"
        ? "Company"
        : null;

  const siteTypeLabel = typedJob.site_type
    ? typedJob.site_type.charAt(0).toUpperCase() + typedJob.site_type.slice(1)
    : null;

  const jobTypeLabel = typedJob.job_type_label ?? null;

  const hasAny =
    priorityLabel || customerTypeLabel || siteTypeLabel || jobTypeLabel;
  if (!hasAny) return null;

  return (
    <div className="flex flex-wrap gap-1 mt-2" aria-label="Job classification">
      {priorityLabel && (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium ${priorityCls}`}
          aria-label={`Priority: ${priorityLabel}`}
        >
          {priorityLabel}
        </span>
      )}
      {customerTypeLabel && (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium bg-neutral-100 text-neutral-600"
          aria-label={`Customer type: ${customerTypeLabel}`}
        >
          {customerTypeLabel}
        </span>
      )}
      {siteTypeLabel && (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium bg-neutral-100 text-neutral-600"
          aria-label={`Site type: ${siteTypeLabel}`}
        >
          {siteTypeLabel}
        </span>
      )}
      {jobTypeLabel && (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium bg-neutral-100 text-neutral-600"
          aria-label={`Job type: ${jobTypeLabel}`}
        >
          {jobTypeLabel}
        </span>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: string | undefined | null }) {
  // Guard against undefined/null — can occur briefly after a PATCH response
  // returns JobResponse (status_id UUID) before the board re-fetches with status_code.
  if (!status) return null;
  const cls = STATUS_CLASSES[status as JobStatus] ?? STATUS_CLASSES.draft;
  const label =
    STATUS_LABELS[status as JobStatus] ??
    status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium ${cls}`}
    >
      {label}
    </span>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-caption font-semibold text-neutral-400 uppercase tracking-wider mb-2">
      {title}
    </h3>
  );
}

// ─── Timezone-safe datetime-local helpers ─────────────────────────────────────

/**
 * Convert a UTC ISO string to a datetime-local input value using the browser's
 * LOCAL timezone so the displayed time matches the user's clock.
 */
function toDatetimeLocalValue(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

/**
 * Convert a datetime-local input value (local time) to a UTC ISO string.
 * new Date(val) parses as local time; .toISOString() converts to UTC.
 */
function fromDatetimeLocalValue(val: string): string | null {
  if (!val) return null;
  return new Date(val).toISOString();
}

// ─── Schedule edit section ────────────────────────────────────────────────────

function ScheduleSection({
  job,
  onUpdated,
}: {
  job: ScheduledJob;
  onUpdated: (job: ScheduledJob) => void;
}) {
  const queryClient = useQueryClient();
  const [startValue, setStartValue] = useState(
    toDatetimeLocalValue(job.scheduled_start_at),
  );
  const [endValue, setEndValue] = useState(
    toDatetimeLocalValue(job.scheduled_end_at),
  );

  const mutation = useMutation({
    mutationFn: async (patch: {
      scheduled_start_at?: string | null;
      scheduled_end_at?: string | null;
    }) => {
      const res = await apiClient.patch<{
        id: string;
        scheduled_start_at: string | null;
        scheduled_end_at: string | null;
        status_id: string;
      }>(`/api/v1/jobs/${job.id}`, patch);
      return res.data;
    },
    onSuccess: (updated) => {
      // The PATCH /api/v1/jobs/{id} response (JobResponse) returns status_id (UUID),
      // NOT the status code string. Merge with the original job to preserve all
      // display fields (status, customer_name, title, etc.) that are not in JobResponse.
      const merged: ScheduledJob = {
        ...job,
        scheduled_start_at:
          updated.scheduled_start_at ?? job.scheduled_start_at,
        scheduled_end_at: updated.scheduled_end_at ?? job.scheduled_end_at,
      };
      onUpdated(merged);
      // Invalidate board queries for both the original date and the new date
      // (job may have moved to a different day).
      const origDate = job.scheduled_start_at?.slice(0, 10) ?? "";
      const newDate = updated.scheduled_start_at?.slice(0, 10) ?? origDate;
      void queryClient.invalidateQueries({ queryKey: ["dispatch-board"] });
      if (origDate !== newDate) {
        void queryClient.invalidateQueries({
          queryKey: DISPATCH_BOARD_QUERY_KEY(origDate, origDate),
        });
      }
    },
  });

  function handleBlur() {
    if (!startValue && !endValue) return;
    mutation.mutate({
      scheduled_start_at: fromDatetimeLocalValue(startValue),
      scheduled_end_at: fromDatetimeLocalValue(endValue),
    });
  }

  return (
    <div className="space-y-2">
      <SectionHeader title="Schedule" />
      <div className="grid grid-cols-1 gap-2">
        <label className="block">
          <span className="text-caption text-neutral-500">Start</span>
          <input
            type="datetime-local"
            value={startValue}
            onChange={(e) => setStartValue(e.target.value)}
            onBlur={handleBlur}
            aria-label="Job start time"
            className="mt-0.5 block w-full rounded border border-neutral-300 bg-white px-2 py-1.5 text-caption text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
        <label className="block">
          <span className="text-caption text-neutral-500">End</span>
          <input
            type="datetime-local"
            value={endValue}
            onChange={(e) => setEndValue(e.target.value)}
            onBlur={handleBlur}
            aria-label="Job end time"
            className="mt-0.5 block w-full rounded border border-neutral-300 bg-white px-2 py-1.5 text-caption text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
      </div>
      {mutation.isPending && (
        <p className="text-caption text-neutral-400">Saving…</p>
      )}
      {mutation.isError && (
        <p className="text-caption text-fault-600">Failed to save schedule.</p>
      )}
    </div>
  );
}

// ─── Status change section ────────────────────────────────────────────────────
// NOTE: PATCH /api/v1/jobs/{id} (JobUpdate schema) does NOT accept a status field —
// status transitions in the backend use a separate workflow endpoint that is not yet
// exposed in the dispatch panel. The current status is shown read-only here.
// To change status, use the full Job Detail page (/jobs/{id}).

function StatusSection({ job }: { job: ScheduledJob }) {
  return (
    <div>
      <SectionHeader title="Status" />
      <div className="flex items-center gap-2">
        <StatusPill status={job.status} />
        <Link
          href={`/jobs/${job.id}`}
          className="text-caption text-brand-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded"
        >
          Change in Job Detail →
        </Link>
      </div>
    </div>
  );
}

// ─── Notes section ────────────────────────────────────────────────────────────

function NotesSection({
  job,
  onUpdated,
}: {
  job: ScheduledJob;
  onUpdated: (job: ScheduledJob) => void;
}) {
  const [notes, setNotes] = useState("");
  const mutation = useMutation({
    mutationFn: async (internal_notes: string) => {
      const res = await apiClient.patch<ScheduledJob>(
        `/api/v1/jobs/${job.id}`,
        { internal_notes },
      );
      return res.data;
    },
    onSuccess: onUpdated,
  });

  return (
    <div>
      <SectionHeader title="Internal Notes" />
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        onBlur={() => mutation.mutate(notes)}
        rows={3}
        placeholder="Add internal notes…"
        aria-label="Internal notes"
        className="w-full rounded border border-neutral-300 bg-white px-2 py-1.5 text-caption text-neutral-900 resize-none focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-neutral-400"
      />
      {mutation.isPending && (
        <p className="text-caption text-neutral-400 mt-0.5">Saving…</p>
      )}
    </div>
  );
}

// ─── TechAssignmentSectionWithInvalidation ────────────────────────────────────
// Thin wrapper over TechAssignmentSection that also invalidates dispatch-board
// queries when an assignment is added or removed. Without this, the week/day grid
// never reflects the crew change until a manual refresh.

function TechAssignmentSectionWithInvalidation({
  jobId,
  job,
  onJobUpdated,
}: {
  jobId: string;
  job: ScheduledJob;
  onJobUpdated: (job: ScheduledJob) => void;
}) {
  const queryClient = useQueryClient();
  const handleAssignmentChanged = useCallback(() => {
    // Update the local panel state (caller re-renders the properties section)
    onJobUpdated(job);
    // Invalidate the entire dispatch-board cache so the grid refetches and
    // shows the updated tech column assignment immediately.
    void queryClient.invalidateQueries({ queryKey: ["dispatch-board"] });
  }, [job, onJobUpdated, queryClient]);

  return (
    <TechAssignmentSection
      jobId={jobId}
      onAssignmentChanged={handleAssignmentChanged}
    />
  );
}

// ─── JobPropertiesPanel ───────────────────────────────────────────────────────

/**
 * JobPropertiesPanel
 *
 * 320px slide-in right panel.
 * Closes on: × button click, Escape key, or click outside.
 */
export function JobPropertiesPanel({
  job,
  onClose,
  onJobUpdated,
}: JobPropertiesPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Escape key to close
  useEffect(() => {
    if (!job) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [job, onClose]);

  // Click outside to close (delayed to avoid instant close from the opener click)
  useEffect(() => {
    if (!job) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const timer = setTimeout(() => {
      document.addEventListener("mousedown", handler);
    }, 100);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("mousedown", handler);
    };
  }, [job, onClose]);

  if (!job) return null;

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label={`Job properties: ${job.title}`}
      className="w-80 flex-shrink-0 flex flex-col h-full border-l border-neutral-200 bg-white overflow-hidden shadow-lg"
    >
      {/* ── Section 1: Header ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-neutral-200 bg-neutral-50">
        <div className="min-w-0 flex-1">
          <h2 className="text-h2 font-semibold text-neutral-900 truncate">
            {job.title}
          </h2>
          <div className="mt-1">
            <StatusPill status={job.status} />
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close job properties panel"
          className="ml-2 flex-shrink-0 p-1 text-neutral-400 hover:text-neutral-600 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 transition-colors"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
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

      {/* ── Scrollable body ───────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {/* ── Section 2: Customer & Site ────────────────────────────────────── */}
        <div>
          <SectionHeader title="Customer & Site" />
          {/* Customer name — primary identifier */}
          <p className="text-body font-medium text-neutral-900">
            {job.customer_name}
          </p>
          {/* DISPATCH-B1.5: site name from Part A — shown between customer and address.
              Conditional: omit when null/undefined (pre-B1.5 boards or unset). */}
          {(job as { site_name?: string | null }).site_name && (
            <p className="text-caption text-neutral-700 mt-0.5">
              {(job as { site_name?: string | null }).site_name}
            </p>
          )}
          {job.site_address && (
            <p className="text-caption text-neutral-500 mt-0.5">
              {job.site_address}
            </p>
          )}
          {/* DISPATCH-B3: read-only classification chips — Priority/Customer Type/Site Type/Job Type */}
          <ClassificationChips job={job} />
        </div>

        {/* ── Section 3: Schedule ───────────────────────────────────────────── */}
        <ScheduleSection job={job} onUpdated={onJobUpdated} />

        {/* ── Section 4: Assigned Technicians ──────────────────────────────── */}
        <div>
          <SectionHeader title="Assigned Technicians" />
          <TechAssignmentSectionWithInvalidation
            jobId={job.id}
            job={job}
            onJobUpdated={onJobUpdated}
          />
        </div>

        {/* ── Section 5: Job Status ──────────────────────────────────────────── */}
        <StatusSection job={job} />

        {/* ── Section 6: Notes ──────────────────────────────────────────────── */}
        <NotesSection job={job} onUpdated={onJobUpdated} />
      </div>

      {/* ── Section 7: Actions footer ─────────────────────────────────────── */}
      <div className="border-t border-neutral-200 px-4 py-3 flex flex-col gap-2 bg-neutral-50">
        <Link
          href={`/jobs/${job.id}`}
          className="block w-full rounded-md border border-brand-600 px-3 py-2 text-center text-caption font-semibold text-brand-600 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 transition-colors"
        >
          View Full Job
        </Link>
        <Link
          href={`/invoices/new?job_id=${job.id}`}
          className="block w-full rounded-md bg-brand-600 px-3 py-2 text-center text-caption font-semibold text-white hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 transition-colors"
        >
          Create Invoice
        </Link>
      </div>
    </div>
  );
}
