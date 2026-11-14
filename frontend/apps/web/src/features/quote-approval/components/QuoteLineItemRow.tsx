/**
 * QuoteLineItemRow — single row in the quote line item table
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteLineItemRow.tsx
 *
 * In review mode: shows amber/green/red tint via DiffView.
 * Has per-row revert button (owner only, when pending edits exist).
 */

"use client";

import React from "react";
import type { QuoteLineItem } from "../hooks/useQuoteDetail";
import type { DiffLineItem } from "@pilot/ui";

interface QuoteLineItemRowProps {
  lineItem: QuoteLineItem;
  diffLineItem?: DiffLineItem;
  onRevertField?: (pendingEditId: string) => void;
  isReviewMode: boolean;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

export function QuoteLineItemRow({
  lineItem,
  diffLineItem,
  onRevertField,
  isReviewMode,
}: QuoteLineItemRowProps) {
  const hasChanges =
    isReviewMode && diffLineItem && diffLineItem.lineChangeType !== "unchanged";

  const rowBgClass = hasChanges
    ? {
        added: "bg-margin-50",
        removed: "bg-fault-50 opacity-75",
        modified: "bg-alert-50",
        unchanged: "",
      }[diffLineItem!.lineChangeType]
    : "";

  return (
    <tr
      className={`border-b border-neutral-200 ${rowBgClass}`}
      aria-label={lineItem.description}
    >
      <td className="py-3 px-4 text-body text-neutral-900">
        {lineItem.description}
        {!lineItem.customer_visible && (
          <span className="ml-2 text-caption text-neutral-400 italic">
            (internal)
          </span>
        )}
      </td>
      <td className="py-3 px-4 text-body text-neutral-600 text-right">
        {lineItem.quantity}
      </td>
      <td className="py-3 px-4 text-body text-neutral-600 text-right">
        {formatCents(lineItem.unit_price_cents)}
      </td>
      <td className="py-3 px-4 text-body font-medium text-neutral-900 text-right">
        {formatCents(lineItem.total_cents)}
      </td>
      {isReviewMode && onRevertField && diffLineItem && hasChanges && (
        <td className="py-3 px-4">
          {diffLineItem.fields.map((field) =>
            field.pendingEditId ? (
              <button
                key={field.fieldName}
                type="button"
                onClick={() => onRevertField(field.pendingEditId!)}
                className="text-caption text-brand-600 hover:text-brand-800 underline block"
                aria-label={`Revert ${field.label ?? field.fieldName} change`}
              >
                Revert {field.label ?? field.fieldName}
              </button>
            ) : null,
          )}
        </td>
      )}
    </tr>
  );
}
