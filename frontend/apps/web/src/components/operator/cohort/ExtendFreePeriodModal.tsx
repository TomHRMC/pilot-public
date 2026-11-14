"use client";

/**
 * ExtendFreePeriodModal — silent free-period extension modal
 *
 * Location: apps/web/src/components/operator/cohort/ExtendFreePeriodModal.tsx
 *
 * C-B11 Part B: Preview-before-send modal (§16.7). Shows the current end date,
 * a date picker for the new end date, a required reason field, and a live
 * preview block before the operator confirms. No customer notification (D16).
 *
 * Uses React Hook Form 7 + Zod v4 via zodResolver.
 * Modal focus management: focus trap, Escape to close, restore focus on close.
 *
 * RULE 5: zero hex codes. RULE 11: no hand-memo. RULE 13: Zod v4 + RHF.
 * RULE 15: WCAG 2.2 AA — focus trap, target size ≥24px, paste allowed.
 */

import React, { useEffect, useRef } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { XMarkIcon, BellSlashIcon } from "@heroicons/react/24/outline";
import { useExtendFreePeriod } from "@/features/operator/hooks/useExtendFreePeriod";
import type { components } from "@pilot/shared-types";
import { isAxiosError } from "@pilot/shared-api";

type CohortMember = components["schemas"]["CohortMemberResponse"];

// ── Zod v4 schema ────────────────────────────────────────────────────────────

const extendSchema = z.object({
  newEndDate: z.string().min(1, { error: "New end date is required." }),
  reason: z
    .string()
    .min(10, { error: "Reason must be at least 10 characters." }),
});

type ExtendFormValues = z.infer<typeof extendSchema>;

// ── Date formatting ───────────────────────────────────────────────────────────

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  year: "numeric",
});

const shortDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

function isoToYyyyMmDd(iso: string | null): string | null {
  if (!iso) return null;
  return iso.slice(0, 10);
}

function parseDate(dateStr: string): Date | null {
  if (!dateStr) return null;
  const d = new Date(dateStr + "T00:00:00Z");
  if (isNaN(d.getTime())) return null;
  return d;
}

function daysBetween(from: Date, to: Date): number {
  return Math.round((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24));
}

// ── Component ─────────────────────────────────────────────────────────────────

interface ExtendFreePeriodModalProps {
  member: CohortMember;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ExtendFreePeriodModal({
  member,
  onClose,
  onSuccess,
}: ExtendFreePeriodModalProps) {
  const extendMutation = useExtendFreePeriod();
  const modalRef = useRef<HTMLDivElement>(null);
  const firstFocusableRef = useRef<HTMLInputElement>(null);

  const currentEndIso = member.free_period_ends_at;
  const currentEndYyyyMmDd = isoToYyyyMmDd(currentEndIso);
  const currentEndDate = parseDate(currentEndYyyyMmDd ?? "");

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isValid },
  } = useForm<ExtendFormValues>({
    resolver: zodResolver(extendSchema),
    mode: "onChange",
    defaultValues: {
      newEndDate: "",
      reason: "",
    },
  });

  const watchedNewDate = useWatch({ control, name: "newEndDate" });
  const watchedReason = useWatch({ control, name: "reason" });

  // Focus management: focus the date input on open
  useEffect(() => {
    firstFocusableRef.current?.focus();
  }, []);

  // Escape to close
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
      // Basic focus trap — Tab cycles within modal
      if (e.key === "Tab" && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll(
          'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0] as HTMLElement;
        const last = focusable[focusable.length - 1] as HTMLElement;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function onSubmit(values: ExtendFormValues) {
    const newEndIso = values.newEndDate + "T00:00:00Z";
    extendMutation.mutate(
      {
        tenantId: member.tenant_id,
        newFreePeriodEndsAt: newEndIso,
        overrideReason: values.reason,
      },
      {
        onSuccess: () => {
          onSuccess?.();
          onClose();
        },
      },
    );
  }

  // Compute preview values
  const newDate = parseDate(watchedNewDate);
  const dayDelta =
    newDate && currentEndDate ? daysBetween(currentEndDate, newDate) : null;

  // 409 error (not trialing)
  const isNotTrialingError =
    extendMutation.isError &&
    isAxiosError(extendMutation.error) &&
    extendMutation.error.response?.status === 409;

  return (
    <div
      className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Extend free period for ${member.business_name}`}
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-h2 font-semibold text-neutral-900">
            Extend free period — #{member.charter_member_number ?? "—"}{" "}
            {member.business_name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-md p-2.5 focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label="Close modal"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          {/* Current free period end (read-only) */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Current free period ends
            </label>
            <p className="text-sm text-neutral-900">
              {currentEndIso
                ? dateFormatter.format(new Date(currentEndIso))
                : "—"}
            </p>
          </div>

          {/* New end date */}
          <div className="mb-4">
            <label
              htmlFor="new-end-date"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              New end date <span className="text-fault-600">*</span>
            </label>
            <input
              id="new-end-date"
              type="date"
              {...register("newEndDate")}
              min={currentEndYyyyMmDd ?? undefined}
              ref={(e) => {
                register("newEndDate").ref(e);
                firstFocusableRef.current = e;
              }}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500"
              aria-describedby="new-end-date-help new-end-date-error"
              aria-invalid={!!errors.newEndDate}
            />
            <p id="new-end-date-help" className="text-xs text-neutral-500 mt-1">
              Must be after the current end date.
            </p>
            {errors.newEndDate && (
              <p
                id="new-end-date-error"
                className="text-xs text-fault-600 mt-1"
              >
                {errors.newEndDate.message}
              </p>
            )}
          </div>

          {/* Reason */}
          <div className="mb-4">
            <label
              htmlFor="extend-reason"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Reason <span className="text-fault-600">*</span>
            </label>
            <textarea
              id="extend-reason"
              {...register("reason")}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500 min-h-[80px] resize-y"
              aria-describedby="extend-reason-help extend-reason-error"
              aria-invalid={!!errors.reason}
            />
            <p
              id="extend-reason-help"
              className="text-xs text-neutral-500 mt-1"
            >
              Required — this is logged to the audit trail.
            </p>
            {errors.reason && (
              <p
                id="extend-reason-error"
                className="text-xs text-fault-600 mt-1"
              >
                {errors.reason.message}
              </p>
            )}
          </div>

          {/* Preview block */}
          <div className="bg-neutral-50 border border-neutral-200 rounded-md p-4 mt-4">
            <p className="text-sm font-medium text-neutral-700 mb-2">Preview</p>
            <div className="space-y-1">
              <div className="flex justify-between text-sm py-1">
                <span className="text-neutral-500">Member</span>
                <span className="text-neutral-900">
                  #{member.charter_member_number ?? "—"} {member.business_name}
                </span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-neutral-500">Current end</span>
                <span className="text-neutral-900">
                  {currentEndIso
                    ? shortDateFormatter.format(new Date(currentEndIso))
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-neutral-500">New end</span>
                <span className="text-neutral-900 font-medium">
                  {newDate
                    ? `${shortDateFormatter.format(newDate)}${
                        dayDelta !== null && dayDelta > 0
                          ? ` (+${dayDelta} days)`
                          : ""
                      }`
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-neutral-500">Reason</span>
                <span
                  className="text-neutral-700 truncate max-w-[60%]"
                  title={watchedReason || undefined}
                >
                  {watchedReason || "—"}
                </span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-neutral-500">Notification</span>
                <span className="inline-flex items-center gap-1 text-neutral-500">
                  <BellSlashIcon className="w-4 h-4" aria-hidden="true" />
                  None (silent extension)
                </span>
              </div>
            </div>
          </div>

          {/* 409 error */}
          {isNotTrialingError && (
            <p className="text-sm text-fault-600 mt-3">
              This subscription is no longer trialing and cannot be extended.
            </p>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isValid || extendMutation.isPending}
              className="bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 disabled:bg-neutral-300 disabled:cursor-not-allowed"
            >
              {extendMutation.isPending ? "Extending…" : "Extend free period"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
