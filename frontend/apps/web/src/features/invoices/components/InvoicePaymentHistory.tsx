/**
 * InvoicePaymentHistory — shows recorded payments for an invoice
 *
 * Location: apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx
 *
 * Pre-work finding: InvoiceResponse does NOT include payments[]. PaymentResponse
 * is returned per POST only. For MVP, show EmptyState with note that payments
 * will appear here after recording. The RecordPaymentModal invalidates
 * ['invoice', invoiceId] which will refresh InvoiceDetailPage on next load.
 *
 * This component accepts optional payments passed in from InvoiceDetailPage.
 */

"use client";

import { EmptyState } from "@pilot/ui/states";

interface PaymentEntry {
  id: string;
  amount_cents: number;
  paid_via: string | null;
  paid_at: string | null;
  psp_provider: string | null;
  customer_payment_comment: string | null;
}

interface InvoicePaymentHistoryProps {
  payments?: PaymentEntry[];
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function InvoicePaymentHistory({
  payments = [],
}: InvoicePaymentHistoryProps) {
  if (payments.length === 0) {
    return (
      <div className="mt-4">
        <h3 className="text-sm font-semibold text-neutral-700 mb-2">
          Payments
        </h3>
        <EmptyState
          type="no-results"
          title="No payments recorded"
          description="Use 'Record Payment' to log a payment against this invoice."
        />
      </div>
    );
  }

  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-neutral-700 mb-2">Payments</h3>
      <div className="rounded-md border border-neutral-200 overflow-hidden">
        <table className="w-full text-sm" data-testid="payment-history-table">
          <thead className="bg-neutral-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-neutral-600">
                Date
              </th>
              <th className="px-4 py-3 text-left font-medium text-neutral-600">
                Amount
              </th>
              <th className="px-4 py-3 text-left font-medium text-neutral-600">
                Method
              </th>
              <th className="px-4 py-3 text-left font-medium text-neutral-600">
                Reference
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {payments.map((p) => (
              <tr key={p.id} className="hover:bg-neutral-50">
                <td className="px-4 py-3 text-neutral-700">
                  {p.paid_at ? new Date(p.paid_at).toLocaleDateString() : "—"}
                </td>
                <td className="px-4 py-3 font-medium text-neutral-900">
                  {formatCents(p.amount_cents)}
                </td>
                <td className="px-4 py-3 text-neutral-600 capitalize">
                  {p.paid_via ? p.paid_via.replace(/_/g, " ") : "—"}
                </td>
                <td className="px-4 py-3 text-neutral-500 text-xs">
                  {p.customer_payment_comment ?? p.psp_provider ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
