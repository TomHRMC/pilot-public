/**
 * ResolveVarianceModal — CE-1 Part C (Web)
 *
 * Location: apps/web/src/features/invoices/components/ResolveVarianceModal.tsx
 *
 * Modal for resolving an overpaid payment. Three resolution options
 * (credit / refund_offline / writeoff) + optional note. One payment per submission.
 *
 * Spec: batch-ce-1-web-ui-design-spec.md §4
 * - 3 verbatim radio options with helper text (§4.4)
 * - Note textarea + character counter (§4.5)
 * - Cancel/Submit buttons (§4.6, submit disabled until radio selected)
 * - Data states: submitting/success/409/422/network (§4.7)
 * - 409 → invalidate + close + notification (§16.4 composition)
 *
 * Accessibility (spec §7.4/§7.5 — binding):
 * - role="dialog" + aria-modal="true" + aria-labelledby
 * - Focus trap with return-focus to trigger
 * - Escape closes except while isPending
 * - Background inert
 * - Labeled controls with aria-describedby
 * - Errors via role="alert"
 *
 * RULE: No hand-written useMemo/useCallback (React Compiler, §32)
 * RULE: Token-only styling (no hardcoded design values, §5)
 * RULE: apiClient via useResolveVariance hook (never raw fetch, §2)
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import {
  XMarkIcon,
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/react/24/outline";
import { useResolveVariance } from "../hooks/useResolveVariance";
import type { ResolveVarianceRequest } from "../hooks/useResolveVariance";
import type { PaymentSummaryEntry } from "../hooks/useInvoice";

interface ResolveVarianceModalProps {
  open: boolean;
  invoiceId: string;
  payment: PaymentSummaryEntry;
  onClose: () => void;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

const RESOLUTION_OPTIONS: {
  value: ResolveVarianceRequest["resolution"];
  label: string;
  helper: string;
}[] = [
  {
    value: "credit",
    label: "Credit forward",
    helper:
      "Apply the overpayment as a credit toward the customer's next invoice.",
  },
  {
    value: "refund_offline",
    label: "Record offline refund",
    helper:
      "Refund happened outside Pilot; this records it. No Stripe refund is issued.",
  },
  {
    value: "writeoff",
    label: "Write off / accept",
    helper: "Accept the overpayment as-is. No refund or credit is issued.",
  },
];

const NOTE_MAX_LENGTH = 1000;

export function ResolveVarianceModal({
  open,
  invoiceId,
  payment,
  onClose,
}: ResolveVarianceModalProps) {
  const { addNotification } = useNotificationQueue();
  const [resolution, setResolution] = useState<
    ResolveVarianceRequest["resolution"] | null
  >(null);
  const [note, setNote] = useState("");
  const [inlineError, setInlineError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const mutation = useResolveVariance({
    invoiceId,
    paymentId: payment.id,
    onSuccess: () => {
      handleClose();
    },
    onError: (error) => {
      if (error.kind === "already_resolved") {
        // §16.4 409-and-refresh: invalidate + close + notification
        addNotification({
          id: `variance-409-${payment.id}`,
          severity: "info",
          title:
            "This overpayment was already resolved. The invoice has been refreshed.",
        });
        handleClose();
      } else {
        // 422 / network — inline error, modal stays open
        setInlineError(error.detail);
      }
    },
  });

  // ── Focus management ──────────────────────────────────────────────────────
  // On open: save trigger, move focus into modal
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement;
      // Focus the close button after render
      const timer = setTimeout(() => {
        closeBtnRef.current?.focus();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // On close: return focus to trigger
  function handleClose() {
    setResolution(null);
    setNote("");
    setInlineError(null);
    onClose();
    // Return focus to the trigger (Resolve button)
    const timer = setTimeout(() => {
      triggerRef.current?.focus();
    }, 0);
    return timer;
  }

  // ── Escape key handler ────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !mutation.isPending) {
        handleClose();
      }
      // Focus trap: Tab cycles within modal
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, mutation.isPending]);

  if (!open) return null;

  const isSubmitting = mutation.isPending;
  const canSubmit = resolution !== null && !isSubmitting;

  function handleSubmit() {
    if (!resolution) return;
    setInlineError(null);
    mutation.mutate({ resolution, note: note.trim() || undefined });
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-neutral-900/50"
        data-testid="resolve-variance-overlay"
        onClick={(e) => {
          if (e.target === e.currentTarget && !isSubmitting) handleClose();
        }}
      />

      {/* Modal panel */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="resolve-variance-title"
        className="fixed inset-0 z-50 flex items-start justify-center p-4"
      >
        <div
          className="bg-white rounded-lg shadow-xl max-w-md w-full mt-16 p-6"
          data-testid="resolve-variance-modal"
        >
          {/* Close button */}
          <button
            ref={closeBtnRef}
            type="button"
            onClick={() => !isSubmitting && handleClose()}
            aria-label="Close"
            disabled={isSubmitting}
            className="absolute top-4 right-4 p-1 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 active:text-neutral-800 transition-colors rounded-md"
            data-testid="resolve-variance-close"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>

          {/* Title */}
          <h2
            id="resolve-variance-title"
            className="text-h2 font-semibold text-neutral-900"
          >
            Resolve overpayment
          </h2>

          {/* Subtitle */}
          <p className="mt-1 text-sm text-neutral-500">
            Payment of {formatCents(payment.amount_cents)} — over by{" "}
            {formatCents(payment.amount_variance_cents)}.
          </p>

          {/* Customer comment */}
          {payment.customer_payment_comment && (
            <p className="mt-2 text-xs text-neutral-600 italic">
              <ChatBubbleLeftRightIcon className="w-4 h-4 text-neutral-400 inline mr-1" />
              Customer note: {payment.customer_payment_comment}
            </p>
          )}

          {/* Form */}
          <form
            className="mt-4 space-y-4"
            aria-busy={isSubmitting}
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit();
            }}
          >
            {/* Resolution radio group */}
            <fieldset
              aria-describedby={
                inlineError ? "resolve-variance-error" : undefined
              }
            >
              <legend className="text-sm font-medium text-neutral-700 mb-2">
                Resolution
              </legend>
              <div className="space-y-2">
                {RESOLUTION_OPTIONS.map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex items-start gap-3 rounded-md border px-3 py-2.5 cursor-pointer hover:bg-neutral-50 focus-within:ring-2 focus-within:ring-brand-500 transition-colors ${
                      resolution === opt.value
                        ? "border-brand-300 bg-brand-50"
                        : "border-neutral-200 bg-white"
                    } ${isSubmitting ? "opacity-60 pointer-events-none" : ""}`}
                    data-testid={`resolution-option-${opt.value}`}
                  >
                    <input
                      type="radio"
                      name="resolution"
                      value={opt.value}
                      checked={resolution === opt.value}
                      onChange={() => setResolution(opt.value)}
                      disabled={isSubmitting}
                      aria-describedby={`resolution-helper-${opt.value}`}
                      className="mt-0.5 h-4 w-4 text-brand-600 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 border-neutral-300"
                    />
                    <div>
                      <span className="text-sm font-medium text-neutral-900">
                        {opt.label}
                      </span>
                      <p
                        id={`resolution-helper-${opt.value}`}
                        className="text-xs text-neutral-500 mt-0.5"
                      >
                        {opt.helper}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </fieldset>

            {/* Note field */}
            <div className="mt-4">
              <label
                htmlFor="resolve-variance-note"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Note (optional)
              </label>
              <textarea
                id="resolve-variance-note"
                rows={3}
                maxLength={NOTE_MAX_LENGTH}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                disabled={isSubmitting}
                aria-describedby="resolve-variance-note-count"
                placeholder="Add a note about this resolution (optional)."
                data-testid="resolve-variance-note"
                className="block w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500 resize-none disabled:bg-neutral-50 disabled:text-neutral-400"
              />
              <p
                id="resolve-variance-note-count"
                className={`mt-1 text-right text-xs ${
                  note.length >= NOTE_MAX_LENGTH
                    ? "text-alert-600"
                    : "text-neutral-500"
                }`}
              >
                {note.length} / {NOTE_MAX_LENGTH}
              </p>
            </div>

            {/* Inline error (422 / network) */}
            {inlineError && (
              <p
                id="resolve-variance-error"
                role="alert"
                className="mt-2 text-xs text-fault-600"
                data-testid="resolve-variance-error"
              >
                {inlineError}
              </p>
            )}

            {/* Action buttons */}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => !isSubmitting && handleClose()}
                disabled={isSubmitting}
                className="inline-flex items-center rounded-md border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 active:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="resolve-variance-cancel"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 active:bg-brand-800 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="resolve-variance-submit"
              >
                {isSubmitting ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 mr-1.5 animate-spin motion-reduce:animate-none" />
                    Resolving…
                  </>
                ) : (
                  "Resolve"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
