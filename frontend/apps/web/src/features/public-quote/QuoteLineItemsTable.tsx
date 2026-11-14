/**
 * QuoteLineItemsTable — FE-B14
 *
 * Location: apps/web/src/features/public-quote/QuoteLineItemsTable.tsx
 *
 * Responsive: table layout on desktop, card stack on mobile (< 640px).
 * Reused by public invoice page for consistent rendering.
 *
 * RULE 1: No useAuth() — unauthenticated surface.
 */

import React from "react";
import type { PublicLineItem } from "./types";

interface QuoteLineItemsTableProps {
  lineItems: PublicLineItem[];
  currency?: string;
  quoteTotalCents: number;
}

function formatCents(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

export function QuoteLineItemsTable({
  lineItems,
  currency = "USD",
  quoteTotalCents,
}: QuoteLineItemsTableProps) {
  return (
    <div className="w-full" data-testid="quote-line-items-table">
      {/* Desktop table */}
      <table className="hidden sm:table w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-neutral-200 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
            <th className="pb-3 pr-4">Description</th>
            <th className="pb-3 pr-4 text-right">Qty</th>
            <th className="pb-3 pr-4 text-right">Unit Price</th>
            <th className="pb-3 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {lineItems.map((item, idx) => (
            <tr
              key={idx}
              className="border-b border-neutral-100 last:border-0"
              data-testid={`line-item-row-${idx}`}
            >
              <td className="py-3 pr-4 text-neutral-800">{item.description}</td>
              <td className="py-3 pr-4 text-right text-neutral-600">
                {item.quantity}
              </td>
              <td className="py-3 pr-4 text-right text-neutral-600">
                {formatCents(item.unitPriceCents, currency)}
              </td>
              <td className="py-3 text-right font-medium text-neutral-800">
                {formatCents(item.totalCents, currency)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td
              colSpan={3}
              className="pt-4 pr-4 text-right text-sm font-semibold text-neutral-700"
            >
              Total
            </td>
            <td
              className="pt-4 text-right text-base font-bold text-neutral-900"
              data-testid="quote-total"
            >
              {formatCents(quoteTotalCents, currency)}
            </td>
          </tr>
        </tfoot>
      </table>

      {/* Mobile card stack */}
      <div
        className="sm:hidden flex flex-col gap-3"
        data-testid="line-items-mobile"
      >
        {lineItems.map((item, idx) => (
          <div
            key={idx}
            className="rounded-lg border border-neutral-200 bg-white p-4"
            data-testid={`line-item-card-${idx}`}
          >
            <p className="text-sm font-medium text-neutral-800">
              {item.description}
            </p>
            <div className="mt-2 flex items-center justify-between text-xs text-neutral-500">
              <span>Qty: {item.quantity}</span>
              <span>{formatCents(item.unitPriceCents, currency)} each</span>
            </div>
            <p className="mt-1 text-right text-sm font-semibold text-neutral-800">
              {formatCents(item.totalCents, currency)}
            </p>
          </div>
        ))}

        {/* Mobile total */}
        <div className="flex items-center justify-between border-t border-neutral-200 pt-3">
          <span className="text-sm font-semibold text-neutral-700">Total</span>
          <span
            className="text-base font-bold text-neutral-900"
            data-testid="quote-total-mobile"
          >
            {formatCents(quoteTotalCents, currency)}
          </span>
        </div>
      </div>
    </div>
  );
}

export { formatCents };
