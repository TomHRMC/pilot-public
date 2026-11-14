/**
 * JobEditModal — pre-populated modal to edit an existing job
 *
 * Location: apps/web/src/features/jobs/components/JobEditModal.tsx
 *
 * FE-B28: Customer <select> + Site <select> replaced with <CustomerCombobox> + <SiteCombobox>.
 * FE-B25: Edit Job UI. Differs from JobFormModal (FE-B24) in:
 * - Props include `currentJob` for pre-population of all form fields
 * - Customer/site comboboxes are pre-selected to current values
 * - When customer changes → site selection is reset (user must re-select)
 * - Submit calls PATCH via useUpdateJob with ONLY changed fields (partial semantics)
 * - Title: "Edit Job" | Submit: "Save Changes"
 *
 * Pattern: Inner component <JobEditContent> is only mounted when open=true,
 * so state resets automatically on close without calling setState in effects.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useUpdateJob } from "../hooks/useUpdateJob";
import type { JobUpdatePayload } from "../hooks/useUpdateJob";
import { CustomerCombobox } from "../../../components/CustomerCombobox";
import { SiteCombobox } from "../../../components/SiteCombobox";

// Converts a UTC ISO 8601 string to a datetime-local input value (YYYY-MM-DDTHH:mm)
// using the browser's LOCAL timezone so the displayed time matches the user's clock.
function toDatetimeLocalValue(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

// Converts a datetime-local input value (local time, YYYY-MM-DDTHH:mm) to a UTC ISO 8601 string.
// new Date(val) parses the string as local time; .toISOString() converts to UTC correctly.
function fromDatetimeLocalValue(val: string): string | null {
  if (!val) return null;
  return new Date(val).toISOString();
}

export interface CurrentJobShape {
  customer_id: string;
  site_id: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
}

interface JobEditModalProps {
  open: boolean;
  onClose: () => void;
  jobId: string;
  currentJob: CurrentJobShape;
  onSuccess?: () => void;
}

/** Inner form — only mounted when modal is open, giving fresh pre-populated state */
function JobEditContent({
  jobId,
  currentJob,
  onClose,
  onSuccess,
}: {
  jobId: string;
  currentJob: CurrentJobShape;
  onClose: () => void;
  onSuccess?: () => void;
}) {
  const firstFocusRef = useRef<HTMLDivElement>(null);
  const { mutate: updateJob, isPending } = useUpdateJob(jobId);

  const [customerId, setCustomerId] = useState(currentJob.customer_id);
  const [siteId, setSiteId] = useState(currentJob.site_id);
  const [scheduledStart, setScheduledStart] = useState(
    toDatetimeLocalValue(currentJob.scheduled_start_at),
  );
  const [scheduledEnd, setScheduledEnd] = useState(
    toDatetimeLocalValue(currentJob.scheduled_end_at),
  );
  const [estimatedMinutes, setEstimatedMinutes] = useState(
    currentJob.estimated_duration_minutes != null
      ? String(currentJob.estimated_duration_minutes)
      : "",
  );
  const [apiError, setApiError] = useState<string | null>(null);

  // Focus trap on mount
  useEffect(() => {
    const timer = setTimeout(() => firstFocusRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  // Reset site when customer changes (only if customer actually changed)
  function handleCustomerChange(id: string) {
    setCustomerId(id);
    if (id !== currentJob.customer_id) {
      setSiteId("");
    } else {
      // Restore original site if customer reverted
      setSiteId(currentJob.site_id);
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

    if (customerId !== currentJob.customer_id) {
      payload.customer_id = customerId;
    }
    if (siteId !== currentJob.site_id) {
      payload.site_id = siteId;
    }

    const newStart = fromDatetimeLocalValue(scheduledStart);
    if (newStart !== currentJob.scheduled_start_at) {
      payload.scheduled_start_at = newStart;
    }

    const newEnd = fromDatetimeLocalValue(scheduledEnd);
    if (newEnd !== currentJob.scheduled_end_at) {
      payload.scheduled_end_at = newEnd;
    }

    const newMinutes = estimatedMinutes ? parseInt(estimatedMinutes, 10) : null;
    if (newMinutes !== currentJob.estimated_duration_minutes) {
      payload.estimated_duration_minutes = newMinutes;
    }

    updateJob(payload, {
      onSuccess: () => {
        onSuccess?.();
        onClose();
      },
      onError: (err) => {
        const message =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ?? "Failed to update job. Please try again.";
        setApiError(message);
      },
    });
  }

  return (
    <div
      ref={firstFocusRef}
      tabIndex={-1}
      className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto focus:outline-none"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2
            id="job-edit-modal-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Edit Job
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Close modal"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Customer combobox — FE-B28: replaced <select> */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Customer <span className="text-fault-600">*</span>
            </label>
            <CustomerCombobox
              value={customerId}
              onChange={handleCustomerChange}
            />
          </div>

          {/* Site combobox — FE-B28: replaced <select> */}
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

          {/* API error */}
          {apiError && (
            <p
              role="alert"
              className="text-sm text-fault-700 bg-fault-50 border border-fault-200 rounded-md px-3 py-2"
            >
              {apiError}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 disabled:opacity-50"
              data-testid="job-edit-submit-btn"
            >
              {isPending ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function JobEditModal({
  open,
  onClose,
  jobId,
  currentJob,
  onSuccess,
}: JobEditModalProps) {
  // Escape key handler lives at the shell level
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="job-edit-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Inner content — remounts on each open, giving fresh pre-populated state */}
      <JobEditContent
        jobId={jobId}
        currentJob={currentJob}
        onClose={onClose}
        onSuccess={onSuccess}
      />
    </div>
  );
}
