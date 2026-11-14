/**
 * QuoteStatusPill — reusable status badge for quote status
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteStatusPill.tsx
 */

import React from "react";

// status_code is a free-form string from the QuoteStatus DB table.
// This union lists known codes; unknown values fall through to the default config.
type KnownQuoteStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "sent"
  | "accepted"
  | "declined"
  | "voided"
  | "expired";

interface QuoteStatusPillProps {
  /** status_code from QuoteResponse / QuoteListItem — nullable per API contract */
  status: string | null | undefined;
  testID?: string;
}

const FALLBACK_CONFIG = {
  label: "Unknown",
  bgClass: "bg-neutral-100",
  textClass: "text-neutral-500",
} as const;

const STATUS_CONFIG: Record<
  KnownQuoteStatus,
  { label: string; bgClass: string; textClass: string }
> = {
  draft: {
    label: "Draft",
    bgClass: "bg-neutral-100",
    textClass: "text-neutral-600",
  },
  pending_approval: {
    label: "Pending Approval",
    bgClass: "bg-alert-100",
    textClass: "text-alert-800",
  },
  approved: {
    label: "Approved",
    bgClass: "bg-margin-100",
    textClass: "text-margin-800",
  },
  rejected: {
    label: "Rejected",
    bgClass: "bg-fault-100",
    textClass: "text-fault-800",
  },
  sent: {
    label: "Sent",
    bgClass: "bg-brand-100",
    textClass: "text-brand-800",
  },
  accepted: {
    label: "Accepted",
    bgClass: "bg-margin-100",
    textClass: "text-margin-800",
  },
  declined: {
    label: "Declined",
    bgClass: "bg-fault-100",
    textClass: "text-fault-800",
  },
  voided: {
    label: "Voided",
    bgClass: "bg-neutral-200",
    textClass: "text-neutral-600",
  },
  expired: {
    label: "Expired",
    bgClass: "bg-neutral-100",
    textClass: "text-neutral-500",
  },
};

export function QuoteStatusPill({ status, testID }: QuoteStatusPillProps) {
  const config =
    status != null
      ? (STATUS_CONFIG[status as KnownQuoteStatus] ?? FALLBACK_CONFIG)
      : FALLBACK_CONFIG;
  const safeStatus = status ?? "unknown";
  return (
    <span
      data-testid={testID ?? `status-pill-${safeStatus}`}
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium ${config.bgClass} ${config.textClass}`}
      aria-label={`Quote status: ${config.label}`}
    >
      {config.label}
    </span>
  );
}
