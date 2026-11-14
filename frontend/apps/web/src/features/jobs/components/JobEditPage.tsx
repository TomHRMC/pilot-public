/**
 * JobEditPage — Full-page edit form for an existing job
 *
 * Location: apps/web/src/features/jobs/components/JobEditPage.tsx
 *
 * JOB-UI-B1: New full-page edit. Fields: title, customer, site, schedule,
 * duration, priority, job_type, status.
 *
 * - Gated by RoleGate permission="jobs.edit"
 * - Partial PATCH via useUpdateJob (only changed fields sent)
 * - On success → navigate back to /jobs/{id}
 * - On 422 → show RFC 7807 detail message inline
 *
 * Pattern: Inner component <JobEditContent> only mounts once the job is loaded,
 * allowing all state to be initialised directly from props in useState() — no
 * useEffect setState cascade (same pattern as JobEditModal).
 *
 * Design decisions (do not re-litigate):
 * - Full-page, not modal (JobEditModal stays dispatch-board schedule-only)
 * - Status editing with forward-transition validation from backend
 * - Priority: standard / urgent / emergency (from CLASS-B1)
 * - Job type from GET /api/v1/job-types via useJobTypes
 */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { RoleGate, LoadingState, ErrorState } from "@pilot/ui";
import { useJob } from "../hooks/useJob";
import type { JobResponse } from "../hooks/useJob";
import { useUpdateJob } from "../hooks/useUpdateJob";
import type { JobUpdatePayload } from "../hooks/useUpdateJob";
import { useJobTypes } from "../hooks/useJobTypes";
import type { JobTypeItem } from "../hooks/useJobTypes";
import { CustomerCombobox } from "../../../components/CustomerCombobox";
import { SiteCombobox } from "../../../components/SiteCombobox";

// ── Datetime local helpers (shared with JobEditModal pattern) ─────────────────

function toDatetimeLocalValue(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function fromDatetimeLocalValue(val: string): string | null {
  if (!val) return null;
  return new Date(val).toISOString();
}

// ── Priority options ──────────────────────────────────────────────────────────

const PRIORITY_OPTIONS = [
  { value: "standard", label: "Standard" },
  { value: "urgent", label: "Urgent" },
  { value: "emergency", label: "Emergency" },
] as const;

// ── Status options (forward transitions enforced by backend) ──────────────────

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "scheduled", label: "Scheduled" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

// ── Inner form — only mounts once job + jobTypes are loaded ───────────────────
// State is initialised from props in useState() — no useEffect needed.

interface JobEditContentProps {
  jobId: string;
  job: JobResponse;
  jobTypes: JobTypeItem[];
}

function JobEditContent({ jobId, job, jobTypes }: JobEditContentProps) {
  const router = useRouter();
  const { mutate: updateJob, isPending } = useUpdateJob(jobId);

  // All state initialised from job prop — no useEffect
  const [title, setTitle] = useState(job.title ?? "");
  const [customerId, setCustomerId] = useState(job.customer_id ?? "");
  const [siteId, setSiteId] = useState(job.site_id ?? "");
  const [scheduledStart, setScheduledStart] = useState(
    toDatetimeLocalValue(job.scheduled_start_at),
  );
  const [scheduledEnd, setScheduledEnd] = useState(
    toDatetimeLocalValue(job.scheduled_end_at),
  );
  const [estimatedMinutes, setEstimatedMinutes] = useState(
    job.estimated_duration_minutes != null
      ? String(job.estimated_duration_minutes)
      : "",
  );
  const [priority, setPriority] = useState(job.priority ?? "standard");
  const [jobTypeId, setJobTypeId] = useState(job.job_type_id ?? "");
  const [statusCode, setStatusCode] = useState(job.status_code ?? "");
  const [apiError, setApiError] = useState<string | null>(null);

  function handleCustomerChange(id: string) {
    setCustomerId(id);
    if (id !== job.customer_id) {
      setSiteId(""); // Reset site when customer changes
    } else {
      setSiteId(job.site_id ?? "");
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);

    if (!customerId) {
      setApiError("Please select a customer.");
      return;
    }
    if (!siteId) {
      setApiError("Please select a site.");
      return;
    }

    // Build partial payload — only include fields that changed
    const payload: JobUpdatePayload = {};

    const trimmedTitle = title.trim() || null;
    if (trimmedTitle !== (job.title ?? null)) {
      payload.title = trimmedTitle;
    }
    if (customerId !== job.customer_id) {
      payload.customer_id = customerId;
    }
    if (siteId !== job.site_id) {
      payload.site_id = siteId;
    }

    const newStart = fromDatetimeLocalValue(scheduledStart);
    if (newStart !== job.scheduled_start_at) {
      payload.scheduled_start_at = newStart;
    }

    const newEnd = fromDatetimeLocalValue(scheduledEnd);
    if (newEnd !== job.scheduled_end_at) {
      payload.scheduled_end_at = newEnd;
    }

    const newMinutes = estimatedMinutes ? parseInt(estimatedMinutes, 10) : null;
    if (newMinutes !== job.estimated_duration_minutes) {
      payload.estimated_duration_minutes = newMinutes;
    }

    const originalPriority = job.priority ?? "standard";
    if (priority && priority !== originalPriority) {
      payload.priority = priority as "standard" | "urgent" | "emergency";
    }

    const newJobTypeId = jobTypeId || null;
    if (newJobTypeId !== (job.job_type_id ?? null)) {
      payload.job_type_id = newJobTypeId;
    }

    if (statusCode && statusCode !== (job.status_code ?? "")) {
      payload.status_code = statusCode;
    }

    updateJob(payload, {
      onSuccess: () => {
        router.push(`/jobs/${jobId}`);
      },
      onError: (err) => {
        // Surface RFC 7807 detail message on 422 (illegal status transition, etc.)
        const errAny = err as {
          response?: { data?: { detail?: string; message?: string } };
          message?: string;
        };
        const message =
          errAny?.response?.data?.detail ??
          errAny?.response?.data?.message ??
          errAny?.message ??
          "Failed to update job. Please try again.";
        setApiError(message);
      },
    });
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-neutral-500 mb-6">
        <Link href="/jobs" className="hover:text-neutral-700 transition-colors">
          Jobs
        </Link>
        <span>/</span>
        <Link
          href={`/jobs/${jobId}`}
          className="hover:text-neutral-700 transition-colors"
        >
          {job.title ?? job.job_number ?? `Job ${jobId.slice(0, 8)}…`}
        </Link>
        <span>/</span>
        <span className="text-neutral-900 font-medium">Edit</span>
      </nav>

      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">Edit Job</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Title */}
        <div>
          <label
            htmlFor="job-edit-title"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Title{" "}
            <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <input
            id="job-edit-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={job.job_number ?? "e.g. Panel Upgrade — Main St"}
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            data-testid="job-edit-title-input"
          />
        </div>

        {/* Customer */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Customer <span className="text-fault-600">*</span>
          </label>
          <CustomerCombobox
            value={customerId}
            onChange={handleCustomerChange}
          />
        </div>

        {/* Site */}
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Site <span className="text-fault-600">*</span>
          </label>
          <SiteCombobox
            customerId={customerId || null}
            value={siteId}
            onChange={setSiteId}
          />
        </div>

        {/* Scheduled Start */}
        <div>
          <label
            htmlFor="job-edit-start"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Scheduled Start{" "}
            <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <input
            id="job-edit-start"
            type="datetime-local"
            value={scheduledStart}
            onChange={(e) => setScheduledStart(e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            data-testid="job-edit-start-input"
          />
        </div>

        {/* Scheduled End */}
        <div>
          <label
            htmlFor="job-edit-end"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Scheduled End{" "}
            <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <input
            id="job-edit-end"
            type="datetime-local"
            value={scheduledEnd}
            onChange={(e) => setScheduledEnd(e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            data-testid="job-edit-end-input"
          />
        </div>

        {/* Estimated Duration */}
        <div>
          <label
            htmlFor="job-edit-duration"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Estimated Duration (minutes){" "}
            <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <input
            id="job-edit-duration"
            type="number"
            min={0}
            step={15}
            value={estimatedMinutes}
            onChange={(e) => setEstimatedMinutes(e.target.value)}
            placeholder="e.g. 120"
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            data-testid="job-edit-duration-input"
          />
        </div>

        {/* Priority */}
        <div>
          <label
            htmlFor="job-edit-priority"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Priority
          </label>
          <select
            id="job-edit-priority"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            data-testid="job-edit-priority-select"
          >
            {PRIORITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Job Type */}
        <div>
          <label
            htmlFor="job-edit-job-type"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Job Type{" "}
            <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <select
            id="job-edit-job-type"
            value={jobTypeId}
            onChange={(e) => setJobTypeId(e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            data-testid="job-edit-job-type-select"
          >
            <option value="">— None —</option>
            {jobTypes.map((jt) => (
              <option key={jt.id} value={jt.id}>
                {jt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label
            htmlFor="job-edit-status"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Status
          </label>
          <select
            id="job-edit-status"
            value={statusCode}
            onChange={(e) => setStatusCode(e.target.value)}
            className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            data-testid="job-edit-status-select"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-neutral-400 mt-1">
            Valid forward transitions only. Illegal transitions will be
            rejected.
          </p>
        </div>

        {/* API / validation error */}
        {apiError && (
          <p
            role="alert"
            data-testid="job-edit-error"
            className="text-sm text-fault-700 bg-fault-50 border border-fault-200 rounded-md px-3 py-2"
          >
            {apiError}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-2 border-t border-neutral-100">
          <Link
            href={`/jobs/${jobId}`}
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 disabled:opacity-50 transition-colors"
            data-testid="job-edit-page-submit-btn"
          >
            {isPending ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Loader shell — fetches job + job-types, then mounts JobEditContent ────────

interface JobEditFormShellProps {
  jobId: string;
}

function JobEditFormShell({ jobId }: JobEditFormShellProps) {
  const { data: job, isLoading: jobLoading, isError: jobError } = useJob(jobId);
  const {
    data: jobTypes,
    isLoading: typesLoading,
    isError: typesError,
  } = useJobTypes();

  if (jobLoading || typesLoading) {
    return (
      <div className="p-6">
        <LoadingState type="full-page" />
      </div>
    );
  }

  if (jobError || !job) {
    return (
      <div className="p-6">
        <ErrorState type="server" description="Failed to load job details." />
      </div>
    );
  }

  if (typesError) {
    return (
      <div className="p-6">
        <ErrorState type="server" description="Failed to load job types." />
      </div>
    );
  }

  // Both loaded — mount content; state initialises from props, no useEffect needed
  return <JobEditContent jobId={jobId} job={job} jobTypes={jobTypes ?? []} />;
}

// ── Public export — wrapped in RoleGate ───────────────────────────────────────

interface JobEditPageProps {
  jobId: string;
}

export function JobEditPage({ jobId }: JobEditPageProps) {
  return (
    <div className="min-h-screen bg-neutral-50">
      <RoleGate permission="jobs.edit">
        <JobEditFormShell jobId={jobId} />
      </RoleGate>
    </div>
  );
}
