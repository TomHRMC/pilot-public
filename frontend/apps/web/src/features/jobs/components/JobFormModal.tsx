/**
 * JobFormModal — modal to create a new job
 *
 * Location: apps/web/src/features/jobs/components/JobFormModal.tsx
 *
 * FE-B31: Added recurrence toggle + pattern/interval/dates config section.
 *         When isRecurring=true, submit calls useCreateRecurrenceRule instead of useCreateJob.
 * FE-B28: Customer <select> + Site <select> replaced with <CustomerCombobox> + <SiteCombobox>.
 * FE-B24: Customer → Site cascade dropdown.
 * - Optional: scheduled_start_at, scheduled_end_at, estimated_duration_minutes
 * - Submit: calls useCreateJob or useCreateRecurrenceRule, closes modal on success
 *
 * Pattern: Inner component <JobFormContent> is only mounted when open=true,
 * so state resets automatically on close without calling setState in effects.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { getApiProblem } from "@pilot/shared-api";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { useCreateJob } from "../hooks/useCreateJob";
import type { JobCreateResponse } from "../hooks/useCreateJob";
import { useCreateRecurrenceRule } from "../hooks/useCreateRecurrenceRule";
import { useJobTypes } from "../hooks/useJobTypes";
import { CustomerCombobox } from "../../../components/CustomerCombobox";
import { SiteCombobox } from "../../../components/SiteCombobox";

interface JobFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (job: JobCreateResponse) => void;
  /** FE-B26: Pre-populate quote_id in the POST /api/v1/jobs/ body */
  prefilledQuoteId?: string;
  /** PLP-FIX-2: preselect the customer (e.g. from the customer detail Jobs tab); still editable. */
  prefilledCustomerId?: string;
}

/** Inner form — only mounted when modal is open, so state is fresh on each open */
function JobFormContent({
  onClose,
  onSuccess,
  prefilledQuoteId,
  prefilledCustomerId,
}: {
  onClose: () => void;
  onSuccess?: (job: JobCreateResponse) => void;
  prefilledQuoteId?: string;
  prefilledCustomerId?: string;
}) {
  const firstFocusRef = useRef<HTMLDivElement>(null);
  const { mutate: createJob, isPending: isJobPending } = useCreateJob();
  const { mutate: createRule, isPending: isRulePending } =
    useCreateRecurrenceRule();
  const { data: jobTypes } = useJobTypes();
  const { addNotification } = useNotificationQueue();

  const [customerId, setCustomerId] = useState(prefilledCustomerId ?? "");
  const [siteId, setSiteId] = useState("");
  // PLP-FIX-5 (Issue 12): Title + Job Type (non-recurrence path only)
  const [jobTitle, setJobTitle] = useState("");
  const [jobTypeId, setJobTypeId] = useState("");
  const [scheduledStart, setScheduledStart] = useState("");
  const [scheduledEnd, setScheduledEnd] = useState("");
  const [estimatedMinutes, setEstimatedMinutes] = useState("");
  const [apiError, setApiError] = useState<string | null>(null);

  // FE-B31: Recurrence toggle state
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrencePattern, setRecurrencePattern] = useState<
    "daily" | "weekly" | "monthly" | "annually"
  >("weekly");
  const [intervalCount, setIntervalCount] = useState(1);
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");

  const isPending = isJobPending || isRulePending;

  // Focus trap on mount
  useEffect(() => {
    const timer = setTimeout(() => firstFocusRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

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

    // FE-B31: Route to recurrence rule endpoint when toggle is on
    if (isRecurring) {
      if (!startsOn) {
        setApiError("Please set a start date for the recurring schedule.");
        return;
      }
      createRule(
        {
          customer_id: customerId,
          site_id: siteId,
          pattern: recurrencePattern,
          interval_count: intervalCount,
          starts_on: startsOn,
          ends_on: endsOn || null,
          estimated_duration_minutes: estimatedMinutes
            ? parseInt(estimatedMinutes, 10)
            : null,
        },
        {
          onSuccess: () => {
            onClose();
          },
          onError: (err) => {
            const problem = getApiProblem(err);
            setApiError(
              problem.detail ??
                "Failed to create recurring job. Please try again.",
            );
          },
        },
      );
      return;
    }

    // Convert datetime-local values (local time) to UTC ISO strings before sending.
    // new Date(val) parses a datetime-local string as local time; .toISOString() converts to UTC.
    const startIso = scheduledStart
      ? new Date(scheduledStart).toISOString()
      : null;
    const endIso = scheduledEnd ? new Date(scheduledEnd).toISOString() : null;

    createJob(
      {
        customer_id: customerId,
        site_id: siteId,
        quote_id: prefilledQuoteId ?? null,
        scheduled_start_at: startIso,
        scheduled_end_at: endIso,
        estimated_duration_minutes: estimatedMinutes
          ? parseInt(estimatedMinutes, 10)
          : null,
        // PLP-FIX-5 (Issue 12): title + job_type_id (optional; omit when empty)
        title: jobTitle.trim() || null,
        job_type_id: jobTypeId || null,
      },
      {
        onSuccess: (job) => {
          // PLP-FIX-5 (Issue 12): success notification with the server-assigned
          // job_number + status_code. Falls back to "Job created." when absent.
          const number = job.job_number ?? "";
          const status = job.status_code ?? "";
          const title = number
            ? `Job ${number} created${status ? ` (${status})` : ""}.`
            : "Job created.";
          addNotification({
            id: `job-created-${job.id}-${Date.now()}`,
            severity: "success",
            title,
            dismissAfterMs: 6000,
          });
          onSuccess?.(job);
          onClose();
        },
        onError: (err) => {
          const problem = getApiProblem(err);
          setApiError(
            problem.detail ?? "Failed to create job. Please try again.",
          );
        },
      },
    );
  }

  const intervalUnitLabel = {
    daily: "day(s)",
    weekly: "week(s)",
    monthly: "month(s)",
    annually: "year(s)",
  }[recurrencePattern];

  return (
    <div
      ref={firstFocusRef}
      tabIndex={-1}
      className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto focus:outline-none"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2
            id="job-form-modal-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Add Job
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
          {/* PLP-FIX-5 (Issue 12): Title input (optional) — non-recurrence path only */}
          {!isRecurring && (
            <div>
              <label
                htmlFor="job-title"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Title{" "}
                <span className="text-neutral-400 font-normal">(optional)</span>
              </label>
              <input
                id="job-title"
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Panel upgrade"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                data-testid="job-title-input"
              />
            </div>
          )}

          {/* Customer combobox — FE-B28: replaced <select> */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Customer <span className="text-fault-600">*</span>
            </label>
            <CustomerCombobox
              value={customerId}
              onChange={(id: string) => {
                setCustomerId(id);
                setSiteId(""); // reset site when customer changes
              }}
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

          {/* PLP-FIX-5 (Issue 12): Job Type select (optional) — non-recurrence path only */}
          {!isRecurring && (
            <div>
              <label
                htmlFor="job-type"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Job Type{" "}
                <span className="text-neutral-400 font-normal">(optional)</span>
              </label>
              <select
                id="job-type"
                value={jobTypeId}
                onChange={(e) => setJobTypeId(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                data-testid="job-type-select"
              >
                <option value="">No type</option>
                {(jobTypes ?? [])
                  .filter((jt) => jt.is_active)
                  .sort((a, b) => a.sort_order - b.sort_order)
                  .map((jt) => (
                    <option key={jt.id} value={jt.id}>
                      {jt.label}
                    </option>
                  ))}
              </select>
            </div>
          )}

          {/* Optional fields — only shown when NOT recurring */}
          {!isRecurring && (
            <>
              {/* Optional: Scheduled Start */}
              <div>
                <label
                  htmlFor="job-start"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Scheduled Start{" "}
                  <span className="text-neutral-400 font-normal">
                    (optional)
                  </span>
                </label>
                <input
                  id="job-start"
                  type="datetime-local"
                  value={scheduledStart}
                  onChange={(e) => setScheduledStart(e.target.value)}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  data-testid="job-start-input"
                />
              </div>

              {/* Optional: Scheduled End */}
              <div>
                <label
                  htmlFor="job-end"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Scheduled End{" "}
                  <span className="text-neutral-400 font-normal">
                    (optional)
                  </span>
                </label>
                <input
                  id="job-end"
                  type="datetime-local"
                  value={scheduledEnd}
                  onChange={(e) => setScheduledEnd(e.target.value)}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  data-testid="job-end-input"
                />
              </div>
            </>
          )}

          {/* Optional: Estimated Duration */}
          <div>
            <label
              htmlFor="job-duration"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Estimated Duration (minutes){" "}
              <span className="text-neutral-400 font-normal">(optional)</span>
            </label>
            <input
              id="job-duration"
              type="number"
              min={0}
              step={15}
              value={estimatedMinutes}
              onChange={(e) => setEstimatedMinutes(e.target.value)}
              placeholder="e.g. 120"
              className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              data-testid="job-duration-input"
            />
          </div>

          {/* FE-B31: Recurrence toggle section */}
          <div className="border-t border-neutral-200 pt-4 mt-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isRecurring}
                onChange={(e) => setIsRecurring(e.target.checked)}
                className="rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
                data-testid="recurrence-toggle"
              />
              <span className="text-sm font-medium text-neutral-700">
                Make this a recurring job
              </span>
            </label>

            {isRecurring && (
              <div
                className="mt-3 space-y-3 pl-6"
                data-testid="recurrence-config"
              >
                {/* Pattern + interval */}
                <div className="flex items-center gap-2 flex-wrap">
                  <select
                    value={recurrencePattern}
                    onChange={(e) =>
                      setRecurrencePattern(
                        e.target.value as
                          | "daily"
                          | "weekly"
                          | "monthly"
                          | "annually",
                      )
                    }
                    className="px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    data-testid="recurrence-pattern"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="annually">Annually</option>
                  </select>
                  <span className="text-sm text-neutral-500">every</span>
                  <input
                    type="number"
                    min={1}
                    value={intervalCount}
                    onChange={(e) => setIntervalCount(+e.target.value)}
                    className="w-16 px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    data-testid="recurrence-interval"
                  />
                  <span className="text-sm text-neutral-500">
                    {intervalUnitLabel}
                  </span>
                </div>

                {/* Starts on */}
                <div>
                  <label
                    htmlFor="recurrence-starts"
                    className="block text-sm font-medium text-neutral-700 mb-1"
                  >
                    Starts <span className="text-fault-600">*</span>
                  </label>
                  <input
                    id="recurrence-starts"
                    type="date"
                    value={startsOn}
                    onChange={(e) => setStartsOn(e.target.value)}
                    required={isRecurring}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    data-testid="recurrence-starts-on"
                  />
                </div>

                {/* Ends on (optional) */}
                <div>
                  <label
                    htmlFor="recurrence-ends"
                    className="block text-sm font-medium text-neutral-700 mb-1"
                  >
                    Ends{" "}
                    <span className="text-neutral-400 font-normal">
                      (optional)
                    </span>
                  </label>
                  <input
                    id="recurrence-ends"
                    type="date"
                    value={endsOn}
                    onChange={(e) => setEndsOn(e.target.value)}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    data-testid="recurrence-ends-on"
                  />
                </div>
              </div>
            )}
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
              data-testid="job-submit-btn"
            >
              {isPending
                ? "Creating…"
                : isRecurring
                  ? "Create Recurring Job"
                  : "Create Job"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function JobFormModal({
  open,
  onClose,
  onSuccess,
  prefilledQuoteId,
  prefilledCustomerId,
}: JobFormModalProps) {
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
      aria-labelledby="job-form-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Inner content — remounts on each open, giving fresh state */}
      <JobFormContent
        onClose={onClose}
        onSuccess={onSuccess}
        prefilledQuoteId={prefilledQuoteId}
        prefilledCustomerId={prefilledCustomerId}
      />
    </div>
  );
}
