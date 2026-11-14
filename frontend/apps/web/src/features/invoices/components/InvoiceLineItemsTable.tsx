/**
 * InvoiceLineItemsTable — renders InvoiceLineResponse[] as a table
 *
 * Location: apps/web/src/features/invoices/components/InvoiceLineItemsTable.tsx
 *
 * Lines are immutable after invoice creation — no edit actions.
 * Columns: Description, Qty, Unit Price, Subtotal, Tax, Total
 * Footer: Subtotal | Tax | Grand Total
 */

"use client";

import type { InvoiceLineResponse } from "../hooks/useInvoice";

interface InvoiceLineItemsTableProps {
  lines: InvoiceLineResponse[];
  subtotalCents: number;
  taxCents: number;
  totalCents: number;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function InvoiceLineItemsTable({
  lines,
  subtotalCents,
  taxCents,
  totalCents,
}: InvoiceLineItemsTableProps) {
  if (lines.length === 0) {
    return (
      <div className="rounded-md border border-neutral-200 p-4 text-sm text-neutral-500 text-center">
        No line items on this invoice.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-neutral-200 overflow-hidden">
      <table className="w-full text-sm" data-testid="invoice-line-items-table">
        <thead className="bg-neutral-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-neutral-600">
              Description
            </th>
            <th className="px-4 py-3 text-right font-medium text-neutral-600 w-16">
              Qty
            </th>
            <th className="px-4 py-3 text-right font-medium text-neutral-600 w-28">
              Unit Price
            </th>
            <th className="px-4 py-3 text-right font-medium text-neutral-600 w-28">
              Subtotal
            </th>
            <th className="px-4 py-3 text-right font-medium text-neutral-600 w-24">
              Tax
            </th>
            <th className="px-4 py-3 text-right font-medium text-neutral-600 w-28">
              Total
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {lines.map((line) => (
            <tr key={line.id} className="hover:bg-neutral-50">
              <td className="px-4 py-3 text-neutral-900">{line.description}</td>
              <td className="px-4 py-3 text-right text-neutral-600">
                {line.quantity}
              </td>
              <td className="px-4 py-3 text-right text-neutral-600">
                {formatCents(line.unit_price_cents)}
              </td>
              <td className="px-4 py-3 text-right text-neutral-600">
                {formatCents(line.subtotal_cents)}
              </td>
              <td className="px-4 py-3 text-right text-neutral-600">
                {formatCents(line.tax_amount_cents)}
              </td>
              <td className="px-4 py-3 text-right font-medium text-neutral-900">
                {formatCents(line.total_cents)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-neutral-50 border-t border-neutral-200">
          <tr>
            <td
              colSpan={3}
              className="px-4 py-3 text-right text-sm text-neutral-500 font-medium"
            >
              Subtotal
            </td>
            <td
              className="px-4 py-3 text-right text-sm text-neutral-700"
              data-testid="invoice-subtotal"
            >
              {formatCents(subtotalCents)}
            </td>
            <td className="px-4 py-3 text-right text-sm text-neutral-500 font-medium">
              Tax
            </td>
            <td
              className="px-4 py-3 text-right text-sm text-neutral-700"
              data-testid="invoice-tax"
            >
              {formatCents(taxCents)}
            </td>
          </tr>
          <tr>
            <td
              colSpan={5}
              className="px-4 py-2 text-right text-sm font-semibold text-neutral-900"
            >
              Grand Total
            </td>
            <td
              className="px-4 py-2 text-right text-sm font-semibold text-neutral-900"
              data-testid="invoice-total"
            >
              {formatCents(totalCents)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
