/**
 * InvoiceDetailPage — full invoice detail surface
 *
 * Location: apps/web/src/features/invoices/components/InvoiceDetailPage.tsx
 *
 * Layout:
 *  1. Header: Invoice number, status badge, customer name, issued/due dates
 *  2. InvoiceLineItemsTable
 *  3. Totals: subtotal, tax, total, balance due
 *  4. InvoicePaymentHistory
 *  5. Action bar: [Send Invoice] [Record Payment] [Copy Public Link]
 *  6. SendInvoicePreviewModal + RecordPaymentModal rendered with open/close state
 *
 * RBAC: Send + Record Payment gated to invoices.edit
 * always-preview-before-send: useSendInvoice fires ONLY from onConfirm of SendInvoicePreviewModal
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { RoleGate } from "@pilot/ui/role-gate";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { useInvoice } from "../hooks/useInvoice";
import { useCustomer } from "../../customers/hooks/useCustomer";
import { useSendInvoice } from "../hooks/useSendInvoice";
import { InvoiceLineItemsTable } from "./InvoiceLineItemsTable";
import { InvoicePaymentHistory } from "./InvoicePaymentHistory";
import { RecordPaymentModal } from "./RecordPaymentModal";
import { SendInvoicePreviewModal } from "./SendInvoicePreviewModal";
// CE-1 Part C — sign-off card + overpayment review
import { InvoiceSignoffCard } from "./InvoiceSignoffCard";
import { OverpaymentReviewBanner } from "./OverpaymentReviewBanner";

interface InvoiceDetailPageProps {
  invoiceId: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  sent: "bg-brand-100 text-brand-700",
  viewed: "bg-brand-100 text-brand-700",
  paid: "bg-margin-100 text-margin-700",
  partially_paid: "bg-alert-100 text-alert-700",
  overdue: "bg-fault-100 text-fault-700",
  void: "bg-neutral-100 text-neutral-500",
};

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function InvoiceDetailPage({ invoiceId }: InvoiceDetailPageProps) {
  const { addNotification } = useNotificationQueue();
  const [sendModalOpen, setSendModalOpen] = useState(false);
  const [recordPaymentOpen, setRecordPaymentOpen] = useState(false);
  const [publicLink, setPublicLink] = useState<string | null>(null);

  const { data: invoice, isLoading, isError, refetch } = useInvoice(invoiceId);
  // Resolve customer name from customer_id — the detail endpoint only returns
  // customer_id (UUID). useCustomer is enabled only after invoice loads.
  const { data: customer } = useCustomer(invoice?.customer_id);

  const { mutate: sendInvoice, isPending: isSending } = useSendInvoice({
    invoiceId,
    onSuccess: (result) => {
      setPublicLink(result.signed_token);
      setSendModalOpen(false);
      addNotification({
        id: `invoice-sent-${invoiceId}`,
        severity: "success",
        title: "Invoice sent successfully. Public link generated.",
      });
    },
    onError: (problem) => {
      setSendModalOpen(false);
      addNotification({
        id: `invoice-send-error-${invoiceId}-${Date.now()}`,
        severity: "error",
        title: problem.title ?? "Failed to send invoice",
        detail:
          problem.detail ?? "Could not send the invoice. Please try again.",
      });
    },
  });

  if (isLoading) {
    return <LoadingState type="inline" label="Loading invoice…" />;
  }

  if (isError || !invoice) {
    return (
      <ErrorState
        type="server"
        title="Could not load invoice"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  const isUnpaid =
    invoice.balance_due_cents > 0 &&
    invoice.status_code !== "void" &&
    invoice.status_code !== "paid";

  const isDraft = invoice.status_code === "draft";

  function handleCopyPublicLink() {
    if (publicLink) {
      void navigator.clipboard.writeText(publicLink);
      addNotification({
        id: `link-copied-${invoiceId}`,
        severity: "success",
        title: "Public link copied to clipboard.",
      });
    } else {
      // Generate first via send
      setSendModalOpen(true);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto" data-testid="invoice-detail-page">
      {/* CE-1 Part C — Overpayment review banner (above breadcrumb) */}
      <RoleGate permission="invoices.view">
        <OverpaymentReviewBanner
          invoiceId={invoiceId}
          payments={invoice.payments ?? []}
        />
      </RoleGate>

      {/* Breadcrumb */}
      <nav className="text-sm text-neutral-500 mb-4">
        <Link href="/invoices" className="hover:text-brand-600">
          Invoices
        </Link>
        <span className="mx-2">/</span>
        <span className="text-neutral-900 font-medium">
          {invoice.invoice_number}
        </span>
      </nav>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-neutral-900">
              {invoice.invoice_number}
            </h1>
            <span
              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                STATUS_COLORS[invoice.status_code] ??
                "bg-neutral-100 text-neutral-600"
              }`}
            >
              {invoice.status_code.replace(/_/g, " ")}
            </span>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-1">
            <p className="text-sm text-neutral-500">
              <span className="font-medium text-neutral-700">Customer:</span>{" "}
              {customer?.display_name ?? (
                <span className="text-neutral-400 italic">Loading…</span>
              )}
            </p>
            {invoice.issued_at && (
              <p className="text-sm text-neutral-500">
                <span className="font-medium text-neutral-700">Issued:</span>{" "}
                {new Date(invoice.issued_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}
            {invoice.due_at && (
              <p className="text-sm text-neutral-500">
                <span className="font-medium text-neutral-700">Due:</span>{" "}
                {new Date(invoice.due_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Line Items */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-neutral-700 mb-2">
          Line Items
        </h2>
        <InvoiceLineItemsTable
          lines={invoice.lines}
          subtotalCents={invoice.subtotal_cents}
          taxCents={invoice.tax_cents}
          totalCents={invoice.total_cents}
        />
      </section>

      {/* Balance Due */}
      <div className="flex justify-end mb-6">
        <div className="rounded-md border border-neutral-200 px-6 py-4 min-w-60 space-y-1">
          <div className="flex justify-between text-sm text-neutral-600">
            <span>Subtotal</span>
            <span>{formatCents(invoice.subtotal_cents)}</span>
          </div>
          <div className="flex justify-between text-sm text-neutral-600">
            <span>Tax</span>
            <span>{formatCents(invoice.tax_cents)}</span>
          </div>
          <div className="flex justify-between text-sm font-semibold text-neutral-900 pt-1 border-t border-neutral-100">
            <span>Total</span>
            <span>{formatCents(invoice.total_cents)}</span>
          </div>
          <div
            className={`flex justify-between text-sm font-bold pt-1 ${
              invoice.balance_due_cents > 0
                ? "text-fault-700"
                : "text-margin-700"
            }`}
          >
            <span>Balance Due</span>
            <span data-testid="balance-due">
              {formatCents(invoice.balance_due_cents)}
            </span>
          </div>
        </div>
      </div>

      {/* Payment History */}
      <InvoicePaymentHistory payments={invoice.payments ?? []} />

      {/* CE-1 Part C — Customer Sign-off card (after payment history) */}
      <RoleGate permission="invoices.view">
        <InvoiceSignoffCard invoiceId={invoiceId} />
      </RoleGate>

      {/* Customer notes */}
      {invoice.customer_notes && (
        <div className="mt-4 rounded-md border border-neutral-200 px-4 py-3">
          <p className="text-xs font-medium text-neutral-500 mb-1">
            Customer Notes
          </p>
          <p className="text-sm text-neutral-700">{invoice.customer_notes}</p>
        </div>
      )}

      {/* Action Bar */}
      <div className="mt-6 flex flex-wrap gap-3">
        {/* Send Invoice — only shown for draft invoices, gated to owner/office_staff/operator */}
        {isDraft && (
          <RoleGate permission="invoices.update">
            <button
              type="button"
              onClick={() => setSendModalOpen(true)}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
              data-testid="send-invoice-btn"
            >
              Send Invoice
            </button>
          </RoleGate>
        )}

        {/* Record Payment — hidden when balance = 0 */}
        {isUnpaid && (
          <RoleGate permission="invoices.update">
            <button
              type="button"
              onClick={() => setRecordPaymentOpen(true)}
              className="px-4 py-2 text-sm font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded-md hover:bg-brand-100 transition-colors"
              data-testid="record-payment-btn"
            >
              Record Payment
            </button>
          </RoleGate>
        )}

        {/* Copy Public Link — PLP-FIX-10 (INV-BUG-16): gated to invoices.update.
            Same operation as Send (POST /{id}/send generates the public link).
            Hidden for accountant + office_staff (lacks invoices.update). */}
        <RoleGate permission="invoices.update">
          <button
            type="button"
            onClick={handleCopyPublicLink}
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
            data-testid="copy-public-link-btn"
          >
            {publicLink ? "Copy Public Link" : "Generate & Copy Link"}
          </button>
        </RoleGate>
      </div>

      {/* Modals */}
      <SendInvoicePreviewModal
        open={sendModalOpen}
        invoiceId={invoiceId}
        invoiceNumber={invoice.invoice_number}
        customerEmail={null} // TODO: enrich from customer data when customer detail hook available
        onClose={() => setSendModalOpen(false)}
        onConfirm={() => sendInvoice()}
        isConfirming={isSending}
      />

      <RecordPaymentModal
        open={recordPaymentOpen}
        invoiceId={invoiceId}
        balanceDueCents={invoice.balance_due_cents}
        onClose={() => setRecordPaymentOpen(false)}
      />
    </div>
  );
}
