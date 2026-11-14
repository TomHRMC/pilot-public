/**
 * DrawRowReadonly — read-only draw row (active / completed / cancelled)
 *
 * Location: apps/web/src/features/billing/components/DrawRowReadonly.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §4.1, §4.2, §5).
 *
 * When the schedule is no longer draft, structural editing is blocked (PATCH/
 * POST/DELETE returns 409 — §G). This row renders the draw as static text +
 * the per-draw lifecycle cell (status badge + invoice link or generate-invoice
 * action slot).
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 */

"use client";

import Link from "next/link";
import {
  ArrowTopRightOnSquareIcon,
  CalendarDaysIcon,
  FlagIcon,
  HandRaisedIcon,
} from "@heroicons/react/24/outline";
import type { PaymentScheduleLineResponse } from "../hooks/usePaymentSchedule";
import { formatCents, formatPercent } from "../utils/format";

interface DrawRowReadonlyProps {
  line: PaymentScheduleLineResponse;
  /** Slot for the generate-invoice action (rendered by the builder for pending draws). */
  generateActionSlot?: React.ReactNode;
}

const STATUS_BADGE_CLASSES: Record<string, string> = {
  pending: "bg-neutral-100 text-neutral-700",
  invoiced: "bg-blue-100 text-blue-700",
  paid: "bg-margin-100 text-margin-700",
  void: "bg-neutral-100 text-neutral-500",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  invoiced: "Invoiced",
  paid: "Paid",
  void: "Void",
};

function TriggerIcon({ type }: { type: string }) {
  if (type === "date")
    return (
      <CalendarDaysIcon
        className="w-4 h-4 text-neutral-400"
        aria-hidden="true"
      />
    );
  if (type === "milestone")
    return <FlagIcon className="w-4 h-4 text-neutral-400" aria-hidden="true" />;
  return (
    <HandRaisedIcon className="w-4 h-4 text-neutral-400" aria-hidden="true" />
  );
}

function triggerDetail(line: PaymentScheduleLineResponse): string {
  if (line.trigger_type === "date") return line.trigger_date ?? "";
  if (line.trigger_type === "milestone") return line.milestone_label ?? "";
  return "Manual";
}

export function DrawRowReadonly({
  line,
  generateActionSlot,
}: DrawRowReadonlyProps) {
  const statusBadgeClass =
    STATUS_BADGE_CLASSES[line.status] ?? STATUS_BADGE_CLASSES.pending;
  const statusLabel = STATUS_LABELS[line.status] ?? line.status;

  return (
    <tr
      data-testid={`draw-row-readonly-${line.id}`}
      className="border-b border-neutral-100"
    >
      {/* Col 1: reorder — removed (read-only) */}
      <td className="w-10 px-4 py-3" />

      {/* Col 2: sequence */}
      <td className="w-10 px-4 py-3 text-center text-neutral-500 text-sm">
        {line.sequence}
      </td>

      {/* Col 3: label */}
      <td className="w-40 px-4 py-3 text-sm text-neutral-900">{line.label}</td>

      {/* Col 4: basis (static label) */}
      <td className="w-44 px-4 py-3 text-sm text-neutral-700">
        {line.basis === "percent" ? "Percent" : "Fixed"}
      </td>

      {/* Col 5: value (static) */}
      <td className="w-32 px-4 py-3 text-sm text-neutral-900 text-right">
        {line.basis === "percent"
          ? `${formatPercent(line.percent)}%`
          : formatCents(line.amount_cents ?? 0)}
      </td>

      {/* Col 6: trigger (static) */}
      <td className="w-48 px-4 py-3 text-sm text-neutral-700">
        <span className="inline-flex items-center gap-1">
          <TriggerIcon type={line.trigger_type} />
          <span>{triggerDetail(line)}</span>
        </span>
      </td>

      {/* Col 7: resolved (display only) */}
      <td
        className="w-28 px-4 py-3 text-sm font-medium text-neutral-900 text-right"
        data-testid={`draw-resolved-${line.id}`}
      >
        {formatCents(line.resolved_amount_cents)}
      </td>

      {/* Col 8: lifecycle cell */}
      <td className="w-12 px-4 py-3 text-sm">
        <div className="flex flex-col items-start gap-1">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium ${statusBadgeClass}`}
          >
            {statusLabel}
          </span>
          {line.invoice_id ? (
            <Link
              href={`/invoices/${line.invoice_id}`}
              className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700 hover:underline text-sm focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded"
              data-testid={`draw-invoice-link-${line.id}`}
            >
              <ArrowTopRightOnSquareIcon
                className="w-4 h-4"
                aria-hidden="true"
              />
              Invoice
            </Link>
          ) : (
            generateActionSlot
          )}
        </div>
      </td>
    </tr>
  );
}
