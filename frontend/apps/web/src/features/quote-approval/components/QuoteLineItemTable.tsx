/**
 * QuoteLineItemTable — renders quote line items with optional track-changes
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteLineItemTable.tsx
 *
 * When in review mode, composes <DiffView variant="quote-line"> inline
 * to show pending edit track-changes rendering.
 */

"use client";

import React from "react";
import { DiffView } from "@pilot/ui";
import { buildQuoteLineDiff } from "@pilot/ui";
import type { QuoteLineItem } from "../hooks/useQuoteDetail";
import type { QuotePendingEditResponse } from "@pilot/ui/hooks";
import { QuoteLineItemRow } from "./QuoteLineItemRow";

interface QuoteLineItemTableProps {
  /** May be undefined/null when the API returns no line_items array */
  lineItems: QuoteLineItem[] | null | undefined;
  pendingEdits?: QuotePendingEditResponse[];
  isReviewMode: boolean;
  onRevertField?: (pendingEditId: string) => void;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

export function QuoteLineItemTable({
  lineItems: lineItemsProp,
  pendingEdits = [],
  isReviewMode,
  onRevertField,
}: QuoteLineItemTableProps) {
  const lineItems = lineItemsProp ?? [];
  const total = lineItems.reduce((sum, li) => sum + li.total_cents, 0);

  // Build the diff data when in review mode
  const diffLineItems =
    isReviewMode && pendingEdits.length > 0
      ? buildQuoteLineDiff({
          allLines: lineItems.map((li) => ({
            id: li.id,
            description: li.description,
            customer_visible: li.customer_visible,
            unit_price_cents: li.unit_price_cents,
            quantity: li.quantity,
            total_cents: li.total_cents,
          })),
          pendingEdits,
        })
      : [];

  const diffByLineId = new Map(diffLineItems.map((d) => [d.lineItemId, d]));

  const hasPendingChanges = diffLineItems.some(
    (d) => d.lineChangeType !== "unchanged",
  );

  return (
    <div>
      {/* Inline diff view above the table when there are changes */}
      {isReviewMode && hasPendingChanges && (
        <div className="mb-4 bg-neutral-50 border border-neutral-200 rounded-md p-4">
          <h3 className="text-body font-medium text-neutral-900 mb-3">
            Pending Changes
          </h3>
          <DiffView
            variant="quote-line"
            lineItems={diffLineItems}
            onRevertField={onRevertField}
            testID="quote-line-diff-view"
          />
        </div>
      )}

      {/* Line items table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left" aria-label="Quote line items">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="py-2 px-4 text-caption font-medium text-neutral-600 uppercase tracking-wide">
                Description
              </th>
              <th className="py-2 px-4 text-caption font-medium text-neutral-600 uppercase tracking-wide text-right">
                Qty
              </th>
              <th className="py-2 px-4 text-caption font-medium text-neutral-600 uppercase tracking-wide text-right">
                Unit Price
              </th>
              <th className="py-2 px-4 text-caption font-medium text-neutral-600 uppercase tracking-wide text-right">
                Total
              </th>
              {isReviewMode && onRevertField && (
                <th className="py-2 px-4 text-caption font-medium text-neutral-600 uppercase tracking-wide">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {lineItems.map((li) => (
              <QuoteLineItemRow
                key={li.id}
                lineItem={li}
                diffLineItem={diffByLineId.get(li.id)}
                onRevertField={onRevertField}
                isReviewMode={isReviewMode}
              />
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-neutral-200">
              <td
                colSpan={isReviewMode && onRevertField ? 4 : 3}
                className="py-3 px-4 text-body font-medium text-neutral-900 text-right"
              >
                Total
              </td>
              <td className="py-3 px-4 text-body font-medium text-neutral-900 text-right">
                {formatCents(total)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
