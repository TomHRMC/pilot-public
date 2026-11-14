/**
 * ArSummaryWidget — AR aging summary on the dashboard
 *
 * Location: apps/web/src/features/dashboard/components/ArSummaryWidget.tsx
 *
 * Data from useArSummary (GET /api/v1/reports/ar-aging).
 * Displays 4 AR aging buckets as a compact card.
 * EmptyState when total_outstanding_cents === 0.
 *
 * UI-FIX-1B: FIX-010a — bucket rows are now clickable Next.js Links.
 */

"use client";

import Link from "next/link";
import { EmptyState, LoadingState } from "@pilot/ui/states";
import { useArSummary } from "../hooks/useArSummary";

interface ArSummaryWidgetProps {
  className?: string;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

export function ArSummaryWidget({ className }: ArSummaryWidgetProps) {
  const { data, isLoading } = useArSummary();

  if (isLoading) {
    return (
      <div className={className}>
        <LoadingState type="inline" label="Loading AR summary…" />
      </div>
    );
  }

  const summary = data?.summary;
  const total = summary?.total_outstanding_cents ?? 0;

  // UI-FIX-1B: FIX-010a — compute due_before dates for AR bucket links
  const today = new Date();
  function toISODateParam(d: Date): string {
    return d.toISOString().split("T")[0]; // YYYY-MM-DD
  }
  const date30dAgo = new Date(today);
  date30dAgo.setDate(today.getDate() - 30);
  const date60dAgo = new Date(today);
  date60dAgo.setDate(today.getDate() - 60);
  const date90dAgo = new Date(today);
  date90dAgo.setDate(today.getDate() - 90);

  if (!summary || total === 0) {
    return (
      <div className={className}>
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-neutral-700 mb-3">
            Accounts Receivable
          </h2>
          <EmptyState
            type="no-results"
            title="No outstanding invoices"
            description="All invoices are paid or there are no invoices yet."
          />
        </div>
      </div>
    );
  }

  const buckets = [
    {
      label: "Current",
      key: "current",
      cents: summary.current_cents,
      colorClass: "text-margin-700",
      href: "/invoices",
    },
    {
      label: "30+ days",
      key: "30d",
      cents: summary.bucket_31_60_cents,
      colorClass: "text-alert-600",
      href: `/invoices?overdue=true&due_before=${toISODateParam(date30dAgo)}`,
    },
    {
      label: "60+ days",
      key: "60d",
      cents: summary.bucket_61_90_cents,
      colorClass: "text-alert-700",
      href: `/invoices?overdue=true&due_before=${toISODateParam(date60dAgo)}`,
    },
    {
      label: "90+ days",
      key: "90d",
      cents: summary.bucket_91_plus_cents,
      colorClass: "text-fault-700",
      href: `/invoices?overdue=true&due_before=${toISODateParam(date90dAgo)}`,
    },
  ];

  return (
    <div className={className} data-testid="ar-summary-widget">
      <div className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-neutral-700 mb-3">
          Accounts Receivable
        </h2>

        <div className="space-y-2">
          {buckets.map((bucket) => (
            <Link
              key={bucket.key}
              href={bucket.href}
              className="flex items-center justify-between hover:bg-neutral-50 rounded px-1 -mx-1 transition-colors"
              data-testid={`ar-bucket-${bucket.key}`}
            >
              <span className="text-sm text-neutral-600">{bucket.label}</span>
              <span className={`text-sm font-medium ${bucket.colorClass}`}>
                {formatCents(bucket.cents)}
              </span>
            </Link>
          ))}
        </div>

        <Link
          href="/invoices?overdue=true"
          className="mt-3 pt-3 border-t border-neutral-100 flex items-center justify-between hover:bg-neutral-50 rounded px-1 -mx-1 transition-colors"
          data-testid="ar-total-outstanding"
        >
          <span className="text-sm font-semibold text-neutral-700">
            Total Outstanding
          </span>
          <span className="text-sm font-bold text-neutral-900">
            {formatCents(total)}
          </span>
        </Link>

        <p className="text-xs text-neutral-400 mt-2">
          As of {data?.as_of_date ?? "today"}
        </p>
      </div>
    </div>
  );
}
