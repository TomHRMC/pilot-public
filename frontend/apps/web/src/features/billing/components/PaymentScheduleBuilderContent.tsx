/**
 * PaymentScheduleBuilderContent — the populated builder (States B/C/D)
 *
 * Location: apps/web/src/features/billing/components/PaymentScheduleBuilderContent.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §3, §4, §5).
 *
 * Renders the schedule header card, the draw editor table (editable when
 * draft, read-only when active/completed/cancelled), the reconciliation bar,
 * and the fixed action footer (Activate / Save draft / Cancel).
 *
 * This component receives a populated PaymentScheduleResponse and the mutation
 * hooks from the parent. It does NOT fetch data — the parent (PaymentScheduleBuilder)
 * handles the 4 data states (isPending skeleton, isError, empty, populated).
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 */

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowLeftIcon,
  PlusIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/outline";
import { BoltIcon as BoltIconSolid } from "@heroicons/react/24/solid";
import type { PaymentScheduleResponse } from "../hooks/usePaymentSchedule";
import type { PaymentScheduleLineUpdate } from "../hooks/useUpdateScheduleLine";
import { useUpdateScheduleLine } from "../hooks/useUpdateScheduleLine";
import { useDeleteScheduleLine } from "../hooks/useDeleteScheduleLine";
import { useAddScheduleLine } from "../hooks/useAddScheduleLine";
import { useActivateSchedule } from "../hooks/useActivateSchedule";
import { DrawRow } from "./DrawRow";
import { ReconciliationBar } from "./ReconciliationBar";
import { GenerateDrawInvoiceButton } from "./GenerateDrawInvoiceButton";
import { formatCents } from "../utils/format";

interface PaymentScheduleBuilderContentProps {
  schedule: PaymentScheduleResponse;
  /** Customer name for display (fetched by parent). */
  customerName?: string;
  /** Site label for display (fetched by parent). */
  siteLabel?: string;
  /** Notify parent of an RFC 7807 error to surface via <NotificationBanner>. */
  onNotifyError?: (detail: string) => void;
}

const STATUS_BADGE_CLASSES: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  active: "bg-blue-100 text-blue-700",
  completed: "bg-margin-100 text-margin-700",
  cancelled: "bg-fault-100 text-fault-500",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  active: "Active",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function PaymentScheduleBuilderContent({
  schedule,
  customerName,
  siteLabel,
  onNotifyError,
}: PaymentScheduleBuilderContentProps) {
  const router = useRouter();
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  const isDraft = schedule.status === "draft";
  const isCancelled = schedule.status === "cancelled";
  const isCompleted = schedule.status === "completed";
  const isEditable = isDraft;

  // ── Mutations (draft-only structural edits) ──────────────────────────────
  const { mutate: updateLine } = useUpdateScheduleLine({
    onError: () =>
      onNotifyError?.("Could not save the draw. Please try again."),
  });

  const { mutate: deleteLine } = useDeleteScheduleLine({
    onError: () =>
      onNotifyError?.("Could not remove the draw. Please try again."),
  });

  const { mutate: addLine } = useAddScheduleLine({
    onError: () => onNotifyError?.("Could not add the draw. Please try again."),
  });

  const { mutate: activateSchedule, isPending: isActivating } =
    useActivateSchedule({
      onSuccess: () => {
        // Cache invalidation in the hook re-fetches → re-renders as State C.
      },
      onResidualMismatch: (detail) => onNotifyError?.(detail),
      onError: () =>
        onNotifyError?.("Could not activate the schedule. Please try again."),
    });

  // ── Handlers ─────────────────────────────────────────────────────────────
  function handleCommit(lineId: string, payload: PaymentScheduleLineUpdate) {
    updateLine({ scheduleId: schedule.id, lineId, payload });
  }

  function handleRemove(lineId: string) {
    setConfirmRemoveId(lineId);
  }

  function confirmRemove() {
    if (!confirmRemoveId) return;
    deleteLine({ scheduleId: schedule.id, lineId: confirmRemoveId });
    setConfirmRemoveId(null);
  }

  function handleReorder(lineId: string, direction: "up" | "down") {
    const lines = schedule.lines;
    const idx = lines.findIndex((l) => l.id === lineId);
    if (idx === -1) return;
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= lines.length) return;
    const target = lines[swapIdx];
    // Swap sequences via PATCH on both lines.
    updateLine({
      scheduleId: schedule.id,
      lineId,
      payload: { sequence: target.sequence },
    });
    updateLine({
      scheduleId: schedule.id,
      lineId: target.id,
      payload: { sequence: lines[idx].sequence },
    });
  }

  function handleAddDraw() {
    const nextSequence =
      schedule.lines.length > 0
        ? Math.max(...schedule.lines.map((l) => l.sequence)) + 1
        : 1;
    addLine({
      scheduleId: schedule.id,
      payload: {
        sequence: nextSequence,
        label: "",
        basis:
          schedule.basis_default === "percent" ? "percent" : "fixed_amount",
        trigger_type: "manual",
      },
    });
  }

  function handleActivate() {
    activateSchedule(schedule.id);
  }

  function handleCancel() {
    router.back();
  }

  // ── Origin link ──────────────────────────────────────────────────────────
  const originHref = schedule.quote_id
    ? `/quotes/${schedule.quote_id}`
    : schedule.job_id
      ? `/jobs/${schedule.job_id}`
      : null;
  const originLabel = schedule.quote_id
    ? "Quote"
    : schedule.job_id
      ? "Job"
      : null;

  // ── Residual gate for Activate ───────────────────────────────────────────
  const residualCents = schedule.residual_cents ?? 0;
  const canActivate = isDraft && residualCents === 0;
  const activateDisabledReason = !canActivate
    ? `Draws must sum to the contract total before activating. ${formatCents(Math.abs(residualCents))} ${residualCents > 0 ? "under" : "over"}-allocated.`
    : undefined;

  return (
    <div className="max-w-5xl mx-auto p-6 pb-24">
      {/* Breadcrumb + Top Action Row */}
      <div className="flex items-center justify-between mb-4">
        <nav className="text-sm text-neutral-500">
          {originHref && originLabel ? (
            <Link href={originHref} className="hover:text-brand-600">
              {originLabel}
            </Link>
          ) : (
            <span>Billing</span>
          )}
          {" / "}
          <span className="text-neutral-900 font-medium">Payment Schedule</span>
        </nav>
        <button
          type="button"
          onClick={handleCancel}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
        >
          <ArrowLeftIcon className="w-4 h-4" aria-hidden="true" />
          Cancel
        </button>
      </div>

      <h1 className="text-h1 font-semibold text-neutral-900 mb-1">
        Payment Schedule
      </h1>

      {/* Cancelled banner (State D) */}
      {isCancelled && (
        <div className="bg-fault-50 border border-fault-200 text-fault-600 rounded-md px-4 py-3 mb-4 flex items-center gap-2">
          <ExclamationCircleIcon
            className="w-5 h-5 flex-shrink-0"
            aria-hidden="true"
          />
          <span className="text-sm font-medium">
            This payment schedule was cancelled.
          </span>
        </div>
      )}

      {/* Schedule header card (§3.1) */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4 scroll-mt-16">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold text-neutral-800">
              Payment Schedule
            </h2>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium ${STATUS_BADGE_CLASSES[schedule.status] ?? STATUS_BADGE_CLASSES.draft}`}
              data-testid="schedule-status-badge"
            >
              {STATUS_LABELS[schedule.status] ?? schedule.status}
            </span>
          </div>
          <div className="flex items-baseline">
            <span className="text-sm text-neutral-500">Contract total</span>
            <span className="text-h3 font-semibold text-neutral-900 ml-2">
              {formatCents(schedule.contract_total_cents)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-6 mt-3 text-sm">
          <span className="text-neutral-500">
            Default basis:{" "}
            <span className="text-neutral-900 font-medium">
              {schedule.basis_default === "percent"
                ? "Percent"
                : "Fixed amount"}
            </span>
          </span>
          {originHref && originLabel && (
            <span className="text-neutral-500">
              From:{" "}
              <Link
                href={originHref}
                className="text-brand-600 hover:text-brand-700 hover:underline"
              >
                {originLabel}
              </Link>
            </span>
          )}
          {(customerName || siteLabel) && (
            <span className="text-neutral-500">
              {customerName}
              {customerName && siteLabel ? " · " : ""}
              {siteLabel}
            </span>
          )}
        </div>
      </section>

      {/* Draw editor card (§3.4) */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4 scroll-mt-16">
        <h2 className="text-base font-semibold text-neutral-800 mb-3">Draws</h2>
        <div className="rounded-md border border-neutral-200 overflow-hidden">
          <table className="w-full text-sm" data-testid="draw-editor-table">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="w-10 px-4 py-3 text-left font-medium text-neutral-700">
                  Reorder
                </th>
                <th className="w-10 px-4 py-3 text-center font-medium text-neutral-700">
                  #
                </th>
                <th className="w-40 px-4 py-3 text-left font-medium text-neutral-700">
                  Label
                </th>
                <th className="w-44 px-4 py-3 text-left font-medium text-neutral-700">
                  Basis
                </th>
                <th className="w-32 px-4 py-3 text-left font-medium text-neutral-700">
                  Value
                </th>
                <th className="w-48 px-4 py-3 text-left font-medium text-neutral-700">
                  Trigger
                </th>
                <th className="w-28 px-4 py-3 text-right font-medium text-neutral-700">
                  Resolved
                </th>
                <th className="w-12 px-4 py-3 text-left font-medium text-neutral-700">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {schedule.lines.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-8 text-center text-neutral-500"
                  >
                    No draws yet.{" "}
                    {isEditable && 'Click "Add draw" to create the first one.'}
                  </td>
                </tr>
              ) : (
                schedule.lines.map((line) => (
                  <DrawRow
                    key={line.id}
                    line={line}
                    isEditable={isEditable}
                    onCommit={handleCommit}
                    onRemove={handleRemove}
                    onReorder={handleReorder}
                    generateActionSlot={
                      !isEditable &&
                      line.status === "pending" &&
                      !line.invoice_id ? (
                        <GenerateDrawInvoiceButton
                          scheduleId={schedule.id}
                          line={line}
                          customerName={customerName}
                          siteLabel={siteLabel}
                          onGenerated={() => {
                            // Cache invalidation in the hook re-fetches → row updates.
                          }}
                          onAlreadyInvoiced={(detail) =>
                            onNotifyError?.(detail)
                          }
                        />
                      ) : !isEditable &&
                        line.status === "pending" &&
                        !line.invoice_id ? (
                        <span className="text-caption text-neutral-400">
                          Trigger not yet reached
                        </span>
                      ) : null
                    }
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Add-draw action (draft only) */}
        {isEditable && (
          <button
            type="button"
            onClick={handleAddDraw}
            className="inline-flex items-center gap-1 mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded p-1"
            data-testid="add-draw-btn"
          >
            <PlusIcon className="w-4 h-4" aria-hidden="true" />
            Add draw
          </button>
        )}
      </section>

      {/* Reconciliation bar (§3.11) */}
      <ReconciliationBar
        scheduledTotalCents={schedule.scheduled_total_cents ?? 0}
        contractTotalCents={schedule.contract_total_cents}
        residualCents={residualCents}
        isCompleted={isCompleted}
      />

      {/* Fixed action footer (§3.12, §3.13, §5) */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-neutral-200 px-6 py-4 flex items-center justify-end gap-3 z-40">
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-300 rounded-md hover:bg-neutral-50 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
        >
          {isCompleted || isCancelled
            ? `Back to ${originLabel ?? "Billing"}`
            : "Cancel"}
        </button>

        {isEditable && (
          <>
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-300 rounded-md hover:bg-neutral-50 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
            >
              Save draft
            </button>
            <button
              type="button"
              onClick={handleActivate}
              disabled={!canActivate || isActivating}
              title={activateDisabledReason}
              aria-describedby={
                activateDisabledReason ? "activate-disabled-reason" : undefined
              }
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
              data-testid="activate-schedule-btn"
            >
              <BoltIconSolid className="w-4 h-4" aria-hidden="true" />
              {isActivating ? "Activating…" : "Activate schedule"}
            </button>
            {activateDisabledReason && (
              <span id="activate-disabled-reason" className="sr-only">
                {activateDisabledReason}
              </span>
            )}
          </>
        )}
      </div>

      {/* Remove confirm modal (§3.9) */}
      {confirmRemoveId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="remove-draw-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setConfirmRemoveId(null);
          }}
          data-testid="remove-draw-confirm"
        >
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6 space-y-4">
            <h2
              id="remove-draw-title"
              className="text-lg font-semibold text-neutral-900"
            >
              Remove draw?
            </h2>
            <p className="text-sm text-neutral-600">
              This will remove the draw from the schedule. You can add it back
              if needed.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setConfirmRemoveId(null)}
                className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-300 rounded-md hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmRemove}
                className="px-4 py-2 text-sm font-medium text-white bg-fault-600 rounded-md hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
                data-testid="remove-draw-confirm-btn"
              >
                Remove draw
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
