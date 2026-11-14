/**
 * DrawRowEditable — editable draw row (draft status only)
 *
 * Location: apps/web/src/features/billing/components/DrawRowEditable.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §3.4–§3.10).
 *
 * Renders one draw as an editable table row: reorder handle, sequence,
 * label input, basis toggle, conditional value input (% or $), trigger
 * control + conditional detail, resolved readout (display only), and the
 * remove action.
 *
 * Validation: Zod v4 via zodResolver (Rule 13 / §34). Errors are non-color-only
 * (aria-invalid + aria-describedby + text message — WCAG 1.4.1).
 *
 * PATCHes on blur (optimistic via the parent's useUpdateScheduleLine wrapper).
 * The parent owns the mutation; this component is a controlled form row.
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 */

"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Bars3Icon,
  TrashIcon,
  CalendarDaysIcon,
  FlagIcon,
  HandRaisedIcon,
} from "@heroicons/react/24/outline";
import type { PaymentScheduleLineResponse } from "../hooks/usePaymentSchedule";
import type { PaymentScheduleLineUpdate } from "../hooks/useUpdateScheduleLine";
import { drawRowSchema, type DrawRowFormValues } from "./drawRowSchema";
import {
  formatCents,
  formatPercent,
  centsToDollars,
  dollarsToCents,
} from "../utils/format";

interface DrawRowEditableProps {
  line: PaymentScheduleLineResponse;
  /** Fired on blur with the partial PATCH payload (draft only). */
  onCommit: (lineId: string, payload: PaymentScheduleLineUpdate) => void;
  /** Fired when the remove button is clicked (after confirm in the parent). */
  onRemove: (lineId: string) => void;
  /** Fired when the reorder handle is activated (arrow keys / drag). */
  onReorder: (lineId: string, direction: "up" | "down") => void;
  /** Whether an optimistic mutation is in flight for this row. */
  isPending?: boolean;
}

export function DrawRowEditable({
  line,
  onCommit,
  onRemove,
  onReorder,
  isPending = false,
}: DrawRowEditableProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<DrawRowFormValues>({
    resolver: zodResolver(drawRowSchema),
    defaultValues: {
      label: line.label,
      basis: line.basis as "percent" | "fixed_amount",
      percentInput: formatPercent(line.percent),
      amountDollars: centsToDollars(line.amount_cents),
      trigger_type: line.trigger_type as "manual" | "date" | "milestone",
      trigger_date: line.trigger_date ?? "",
      milestone_label: line.milestone_label ?? "",
    },
  });

  // eslint-disable-next-line react-hooks/incompatible-library
  const basis = watch("basis");

  const triggerType = watch("trigger_type");

  // Re-sync when the line prop changes (e.g. after a refetch invalidation).
  useEffect(() => {
    setValue("label", line.label);
    setValue("basis", line.basis as "percent" | "fixed_amount");
    setValue("percentInput", formatPercent(line.percent));
    setValue("amountDollars", centsToDollars(line.amount_cents));
    setValue(
      "trigger_type",
      line.trigger_type as "manual" | "date" | "milestone",
    );
    setValue("trigger_date", line.trigger_date ?? "");
    setValue("milestone_label", line.milestone_label ?? "");
  }, [line, setValue]);

  // Build the PATCH payload from form values.
  function buildPayload(values: DrawRowFormValues): PaymentScheduleLineUpdate {
    const payload: PaymentScheduleLineUpdate = {
      label: values.label,
      basis: values.basis,
      trigger_type: values.trigger_type,
    };
    if (values.basis === "percent") {
      payload.percent = values.percentInput;
      payload.amount_cents = null;
    } else {
      const cents = dollarsToCents(values.amountDollars);
      payload.amount_cents = cents;
      payload.percent = null;
    }
    if (values.trigger_type === "date") {
      payload.trigger_date = values.trigger_date;
      payload.milestone_label = null;
    } else if (values.trigger_type === "milestone") {
      payload.milestone_label = values.milestone_label;
      payload.trigger_date = null;
    } else {
      payload.trigger_date = null;
      payload.milestone_label = null;
    }
    return payload;
  }

  // Blur handler — validate then commit.
  const onBlurred = handleSubmit((values) => {
    onCommit(line.id, buildPayload(values));
  });

  // Basis toggle — clears the now-irrelevant value field client-side (§3.6).
  function handleBasisChange(nextBasis: "percent" | "fixed_amount") {
    if (nextBasis === basis) return;
    setValue("basis", nextBasis, { shouldValidate: true });
    if (nextBasis === "percent") {
      setValue("amountDollars", "");
    } else {
      setValue("percentInput", "");
    }
  }

  function handleTriggerChange(next: "manual" | "date" | "milestone") {
    setValue("trigger_type", next, { shouldValidate: true });
  }

  return (
    <tr
      data-testid={`draw-row-editable-${line.id}`}
      className="border-b border-neutral-100 hover:bg-neutral-50"
    >
      {/* Col 1: reorder handle (≥24×24px hit area) */}
      <td className="w-10 px-4 py-3">
        <button
          type="button"
          className="p-1 rounded text-neutral-400 hover:text-neutral-700 cursor-grab active:cursor-grabbing focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
          aria-label={`Reorder draw ${line.sequence}: ${line.label}`}
          onClick={() => onReorder(line.id, "up")}
          onKeyDown={(e) => {
            if (e.key === "ArrowUp") {
              e.preventDefault();
              onReorder(line.id, "up");
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              onReorder(line.id, "down");
            }
          }}
        >
          <Bars3Icon className="w-5 h-5" aria-hidden="true" />
        </button>
      </td>

      {/* Col 2: sequence */}
      <td className="w-10 px-4 py-3 text-center text-neutral-500 text-sm">
        {line.sequence}
      </td>

      {/* Col 3: label input */}
      <td className="w-40 px-4 py-3">
        <input
          type="text"
          {...register("label")}
          placeholder="Draw label (e.g. Rough-in)"
          aria-label={`Draw label for sequence ${line.sequence}`}
          aria-invalid={!!errors.label}
          aria-describedby={
            errors.label ? `draw-label-err-${line.id}` : undefined
          }
          className="w-full border border-neutral-300 rounded-md px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-500"
          onBlur={onBlurred}
        />
        {errors.label && (
          <p
            id={`draw-label-err-${line.id}`}
            className="text-xs text-fault-600 mt-1"
          >
            {errors.label.message}
          </p>
        )}
      </td>

      {/* Col 4: basis toggle (segmented) */}
      <td className="w-44 px-4 py-3">
        <div
          role="group"
          aria-label={`Basis for sequence ${line.sequence}`}
          className="bg-neutral-100 rounded-md p-0.5 inline-flex text-xs"
        >
          <button
            type="button"
            onClick={() => handleBasisChange("percent")}
            className={
              basis === "percent"
                ? "bg-white shadow-sm rounded px-2 py-1 text-xs font-medium text-neutral-900 focus-visible:ring-2 focus-visible:ring-brand-500"
                : "px-2 py-1 text-xs font-medium text-neutral-500 hover:text-neutral-700 focus-visible:ring-2 focus-visible:ring-brand-500 rounded"
            }
          >
            Percent
          </button>
          <button
            type="button"
            onClick={() => handleBasisChange("fixed_amount")}
            className={
              basis === "fixed_amount"
                ? "bg-white shadow-sm rounded px-2 py-1 text-xs font-medium text-neutral-900 focus-visible:ring-2 focus-visible:ring-brand-500"
                : "px-2 py-1 text-xs font-medium text-neutral-500 hover:text-neutral-700 focus-visible:ring-2 focus-visible:ring-brand-500 rounded"
            }
          >
            Fixed
          </button>
        </div>
      </td>

      {/* Col 5: value input (conditional on basis) */}
      <td className="w-32 px-4 py-3">
        {basis === "percent" ? (
          <div className="flex items-center">
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              {...register("percentInput")}
              aria-label={`Percent of contract total for sequence ${line.sequence}`}
              aria-invalid={!!errors.percentInput}
              aria-describedby={
                errors.percentInput ? `draw-pct-err-${line.id}` : undefined
              }
              className="w-24 border border-neutral-300 rounded-md px-2 py-2 text-sm text-right text-neutral-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-500"
              onBlur={onBlurred}
            />
            <span className="text-neutral-500 ml-1 text-sm">%</span>
            {errors.percentInput && (
              <p
                id={`draw-pct-err-${line.id}`}
                className="text-xs text-fault-600 mt-1 sr-only"
              >
                {errors.percentInput.message}
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center">
            <span className="text-neutral-500 mr-1 text-sm">$</span>
            <input
              type="number"
              step="0.01"
              min="0"
              {...register("amountDollars")}
              aria-label={`Fixed dollar amount for sequence ${line.sequence}`}
              aria-invalid={!!errors.amountDollars}
              aria-describedby={
                errors.amountDollars ? `draw-amt-err-${line.id}` : undefined
              }
              className="w-24 border border-neutral-300 rounded-md px-2 py-2 text-sm text-right text-neutral-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-500"
              onBlur={onBlurred}
            />
            {errors.amountDollars && (
              <p
                id={`draw-amt-err-${line.id}`}
                className="text-xs text-fault-600 mt-1 sr-only"
              >
                {errors.amountDollars.message}
              </p>
            )}
          </div>
        )}
        {(errors.percentInput || errors.amountDollars) && (
          <p className="text-xs text-fault-600 mt-1">
            {errors.percentInput?.message ?? errors.amountDollars?.message}
          </p>
        )}
      </td>

      {/* Col 6: trigger control + conditional detail */}
      <td className="w-48 px-4 py-3">
        <div className="flex items-center">
          <span className="mr-1">
            {triggerType === "date" ? (
              <CalendarDaysIcon
                className="w-4 h-4 text-neutral-400"
                aria-hidden="true"
              />
            ) : triggerType === "milestone" ? (
              <FlagIcon
                className="w-4 h-4 text-neutral-400"
                aria-hidden="true"
              />
            ) : (
              <HandRaisedIcon
                className="w-4 h-4 text-neutral-400"
                aria-hidden="true"
              />
            )}
          </span>
          <select
            {...register("trigger_type")}
            onChange={(e) =>
              handleTriggerChange(
                e.target.value as "manual" | "date" | "milestone",
              )
            }
            aria-label={`Trigger type for sequence ${line.sequence}`}
            className="border border-neutral-300 rounded-md px-2 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500"
          >
            <option value="manual">Manual</option>
            <option value="date">On date</option>
            <option value="milestone">On milestone</option>
          </select>
          {triggerType === "date" && (
            <input
              type="date"
              {...register("trigger_date")}
              aria-label={`Trigger date for sequence ${line.sequence}`}
              aria-invalid={!!errors.trigger_date}
              aria-describedby={
                errors.trigger_date ? `draw-date-err-${line.id}` : undefined
              }
              className="ml-2 w-40 border border-neutral-300 rounded-md px-2 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500"
              onBlur={onBlurred}
            />
          )}
          {triggerType === "milestone" && (
            <input
              type="text"
              {...register("milestone_label")}
              placeholder="Milestone (e.g. Rough-in complete)"
              aria-label={`Milestone label for sequence ${line.sequence}`}
              aria-invalid={!!errors.milestone_label}
              aria-describedby={
                errors.milestone_label ? `draw-ms-err-${line.id}` : undefined
              }
              className="ml-2 w-48 border border-neutral-300 rounded-md px-2 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500"
              onBlur={onBlurred}
            />
          )}
          {triggerType === "manual" && (
            <span className="ml-2 text-caption text-neutral-400">
              Invoiced manually
            </span>
          )}
        </div>
        {(errors.trigger_date || errors.milestone_label) && (
          <p className="text-xs text-fault-600 mt-1">
            {errors.trigger_date?.message ?? errors.milestone_label?.message}
          </p>
        )}
      </td>

      {/* Col 7: resolved readout (display only — backend-computed) */}
      <td
        className="w-28 px-4 py-3 text-sm font-medium text-neutral-900 text-right"
        data-testid={`draw-resolved-${line.id}`}
      >
        {formatCents(line.resolved_amount_cents)}
      </td>

      {/* Col 8: remove action (draft) or pending badge */}
      <td className="w-12 px-4 py-3">
        {isPending ? (
          <span
            className="text-caption text-neutral-400"
            data-testid={`draw-pending-${line.id}`}
          >
            Saving…
          </span>
        ) : (
          <button
            type="button"
            onClick={() => onRemove(line.id)}
            className="p-1.5 rounded-md text-neutral-400 hover:text-fault-600 hover:bg-fault-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
            aria-label={`Remove draw ${line.sequence}: ${line.label}`}
          >
            <TrashIcon className="w-4 h-4" aria-hidden="true" />
          </button>
        )}
      </td>
    </tr>
  );
}
