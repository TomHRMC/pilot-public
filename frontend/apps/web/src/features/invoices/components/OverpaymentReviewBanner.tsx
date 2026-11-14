/**
 * OverpaymentReviewBanner — CE-1 Part C (Web)
 *
 * Location: apps/web/src/features/invoices/components/OverpaymentReviewBanner.tsx
 *
 * Warning banner that renders when any payment on the invoice has
 * amount_variance_cents > 0 AND variance_resolution IS NULL.
 * Collapses to a quiet resolved line when all overpayments are resolved.
 * Returns null (hidden) when no payment has a variance.
 *
 * Spec: batch-ce-1-web-ui-design-spec.md §3
 * - Active state: alert tokens, headline copy, per-payment rows, customer comment,
 *   Resolve button behind <RoleGate permission="invoices.update">
 * - Resolved state: neutral tokens, collapsed line per resolved payment
 * - Hidden state: returns null
 *
 * RULE: No hand-written useMemo (React Compiler, §32) — the unresolvedOverpayments
 *       filter is a plain derived value (spec §3.1).
 * RULE: Token-only styling (no hardcoded design values, §5)
 * RULE: RBAC hide-not-disable (§6) — Resolve button wrapped in <RoleGate>
 */

"use client";

import { useState } from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/react/24/solid";
import { CheckCircleIcon as CheckCircleOutlineIcon } from "@heroicons/react/24/outline";
import type { PaymentSummaryEntry } from "../hooks/useInvoice";
import { ResolveVarianceModal } from "./ResolveVarianceModal";

interface OverpaymentReviewBannerProps {
  invoiceId: string;
  payments: PaymentSummaryEntry[];
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const RESOLUTION_LABELS: Record<string, string> = {
  credit: "credit forward",
  refund_offline: "offline refund",
  writeoff: "write off",
};

export function OverpaymentReviewBanner({
  invoiceId,
  payments,
}: OverpaymentReviewBannerProps) {
  const [modalPaymentId, setModalPaymentId] = useState<string | null>(null);

  // Pure derived filter — no memoization (React Compiler, §32)
  const unresolvedOverpayments = (payments ?? []).filter(
    (p) => p.amount_variance_cents > 0 && p.variance_resolution === null,
  );

  const resolvedOverpayments = (payments ?? []).filter(
    (p) => p.amount_variance_cents > 0 && p.variance_resolution !== null,
  );

  // Hidden state — no variance at all
  if (
    unresolvedOverpayments.length === 0 &&
    resolvedOverpayments.length === 0
  ) {
    return null;
  }

  // Resolved state — all overpayments resolved, none unresolved
  if (unresolvedOverpayments.length === 0 && resolvedOverpayments.length > 0) {
    return (
      <div
        className="mb-4 rounded-md border border-neutral-200 bg-neutral-50 px-4 py-2"
        data-testid="overpayment-resolved-line"
      >
        <div className="flex items-center gap-2">
          <CheckCircleOutlineIcon className="w-4 h-4 text-margin-600" />
          <div className="space-y-0.5">
            {resolvedOverpayments.map((p) => (
              <p key={p.id} className="text-xs text-neutral-600">
                Overpayment of {formatCents(p.amount_variance_cents)} resolved
                as{" "}
                {RESOLUTION_LABELS[p.variance_resolution!] ??
                  p.variance_resolution}{" "}
                on {formatDate(p.variance_resolved_at!)}.
              </p>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Active state — unresolved overpayments exist
  const firstUnresolved = unresolvedOverpayments[0];

  return (
    <>
      <div
        className="mb-4 rounded-md border border-alert-200 bg-alert-50 px-4 py-3"
        data-testid="overpayment-review-banner"
      >
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon className="w-5 h-5 text-alert-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            {/* Headline — anchored on arch §18.5 */}
            <p
              className="text-sm font-medium text-alert-800"
              data-testid="overpayment-headline"
            >
              Customer paid {formatCents(firstUnresolved.amount_variance_cents)}{" "}
              over invoice total — review.
            </p>

            {/* Per-payment rows (when >1) */}
            {unresolvedOverpayments.length > 1 && (
              <div className="space-y-0.5">
                {unresolvedOverpayments.map((p) => (
                  <p
                    key={p.id}
                    className="text-sm text-alert-700"
                    data-testid="overpayment-payment-row"
                  >
                    Payment of {formatCents(p.amount_cents)} on{" "}
                    {p.paid_at ? formatDate(p.paid_at) : "—"} — over by{" "}
                    {formatCents(p.amount_variance_cents)}.
                  </p>
                ))}
              </div>
            )}

            {/* Customer comment */}
            {firstUnresolved.customer_payment_comment && (
              <p
                className="text-xs text-alert-700 italic"
                data-testid="overpayment-customer-comment"
              >
                <ChatBubbleLeftRightIcon className="w-4 h-4 text-alert-500 inline mr-1" />
                Customer note: {firstUnresolved.customer_payment_comment}
              </p>
            )}

            {/* Resolve button — gated to invoices.update (owner only per ADR-0010) */}
            <RoleGate permission="invoices.update">
              <button
                type="button"
                onClick={() => setModalPaymentId(firstUnresolved.id)}
                className="mt-2 inline-flex items-center rounded-md border border-alert-300 bg-white px-3 py-2 text-sm font-medium text-alert-700 hover:bg-alert-100 active:bg-alert-200 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 transition-colors duration-150 ease-in-out motion-reduce:transition-none"
                data-testid="resolve-variance-btn"
              >
                <CheckCircleIcon className="w-4 h-4 mr-1.5" />
                Resolve
              </button>
            </RoleGate>
          </div>
        </div>
      </div>

      {/* Modal — rendered when a payment is selected for resolution */}
      {modalPaymentId && (
        <ResolveVarianceModal
          open={!!modalPaymentId}
          invoiceId={invoiceId}
          payment={firstUnresolved}
          onClose={() => setModalPaymentId(null)}
        />
      )}
    </>
  );
}
