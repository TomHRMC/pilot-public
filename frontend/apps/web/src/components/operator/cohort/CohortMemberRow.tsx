"use client";

/**
 * CohortMemberRow — cell renderers for a single Charter member
 *
 * Location: apps/web/src/components/operator/cohort/CohortMemberRow.tsx
 *
 * C-B11 Part B: Per the UI design spec §12, rows are rendered via TanStack
 * Table columnDef.cell functions. This module exports helper render functions
 * + a getRowClassName utility for alert-level row styling.
 *
 * Alert-level styling is color-independent (WCAG 1.4.1): every alert level
 * pairs a color token with an icon AND a text label.
 *
 * RULE 5: zero hex codes — all tokens.
 * RULE 11: no hand-memo — React Compiler handles it.
 */

import React from "react";
import {
  ExclamationTriangleIcon,
  ClockIcon,
  CheckCircleIcon,
  CreditCardIcon,
  MinusCircleIcon,
} from "@heroicons/react/24/outline";
import type { components } from "@pilot/shared-types";

export type CohortMember = components["schemas"]["CohortMemberResponse"];

export type AlertLevel = "red" | "amber" | "none";

// ── Row class name (applied to <tr> via PilotTable getRowClassName) ───────────

export function getCohortRowClassName(member: CohortMember): string {
  const level = member.alert_level as AlertLevel;
  if (level === "red") {
    return "bg-fault-50 border-l-4 border-fault-500 hover:bg-fault-100 transition-colors";
  }
  if (level === "amber") {
    return "bg-alert-50 border-l-4 border-alert-500 hover:bg-alert-100 transition-colors";
  }
  return "hover:bg-neutral-50 transition-colors";
}

// ── Cell renderers ────────────────────────────────────────────────────────────

/** Column 1 — Member: "#1 — Acme Electric" */
export function renderMemberCell(member: CohortMember): React.ReactNode {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm">
        <span className="font-medium text-neutral-900">
          #{member.charter_member_number ?? "—"}
        </span>
        <span className="text-neutral-400"> — </span>
        <span className="text-neutral-700">{member.business_name}</span>
      </span>
    </div>
  );
}

/** Column 2 — Days left */
export function renderDaysLeftCell(member: CohortMember): React.ReactNode {
  if (member.days_remaining === null) {
    return <span className="text-sm text-neutral-400">—</span>;
  }
  const isAmber = member.days_remaining <= 14;
  return (
    <span
      className={`text-sm tabular-nums ${
        isAmber ? "text-alert-700 font-medium" : "text-neutral-900"
      }`}
    >
      {member.days_remaining}
    </span>
  );
}

/** Column 3 — Stripe status badge */
export function renderStripeStatusCell(member: CohortMember): React.ReactNode {
  const status = member.stripe_status;
  const badgeClasses =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium";

  if (status === "trialing") {
    return (
      <span className={`${badgeClasses} bg-blue-100 text-blue-700`}>
        Trialing
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className={`${badgeClasses} bg-margin-100 text-margin-700`}>
        Active
      </span>
    );
  }
  if (status === "paused") {
    return (
      <span className={`${badgeClasses} bg-neutral-100 text-neutral-500`}>
        Paused
      </span>
    );
  }
  return (
    <span className={`${badgeClasses} bg-neutral-100 text-neutral-500`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

/** Column 4 — Card (payment method on file) */
export function renderCardCell(member: CohortMember): React.ReactNode {
  if (member.has_payment_method) {
    return (
      <div className="flex justify-center">
        <CreditCardIcon
          className="w-4 h-4 text-neutral-400"
          aria-label="Payment method on file"
        />
      </div>
    );
  }
  return (
    <div className="flex justify-center">
      <MinusCircleIcon
        className="w-4 h-4 text-neutral-300"
        aria-label="No payment method"
      />
    </div>
  );
}

/** Column 5 — 10DLC messaging status badge */
export function renderMessagingStatusCell(
  member: CohortMember,
): React.ReactNode {
  const status = member.messaging_status;
  const badgeClasses =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium";

  if (status === "active") {
    return (
      <span className={`${badgeClasses} bg-margin-100 text-margin-700`}>
        Active
      </span>
    );
  }
  if (status === "pending") {
    return (
      <span className={`${badgeClasses} bg-alert-100 text-alert-700`}>
        Pending
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className={`${badgeClasses} bg-fault-100 text-fault-600`}>
        Failed
      </span>
    );
  }
  // not_started or unknown
  return (
    <span className={`${badgeClasses} bg-neutral-100 text-neutral-500`}>
      Not started
    </span>
  );
}

/** Column 6 — Customers count */
export function renderCustomerCountCell(member: CohortMember): React.ReactNode {
  return (
    <span className="text-sm text-neutral-900 tabular-nums text-center block">
      {member.customer_count}
    </span>
  );
}

/** Column 7 — Invoices count */
export function renderInvoiceCountCell(member: CohortMember): React.ReactNode {
  return (
    <span className="text-sm text-neutral-900 tabular-nums text-center block">
      {member.invoice_count}
    </span>
  );
}

/** Column 8 — Last job (days since) */
export function renderLastJobCell(member: CohortMember): React.ReactNode {
  if (member.days_since_last_job === null) {
    return <span className="text-sm text-fault-600 font-medium">Never</span>;
  }
  const isRed = member.days_since_last_job > 7;
  return (
    <span
      className={`text-sm tabular-nums ${
        isRed ? "text-fault-600 font-medium" : "text-neutral-700"
      }`}
    >
      {member.days_since_last_job}d
    </span>
  );
}

/** Column 9 — Alert level (icon + text, color-independent) */
export function renderAlertCell(member: CohortMember): React.ReactNode {
  const level = member.alert_level as AlertLevel;

  if (level === "red") {
    return (
      <td className="px-4 py-3" aria-label="Alert: activation risk">
        <span className="inline-flex items-center gap-1.5 text-fault-600 text-sm font-medium">
          <ExclamationTriangleIcon className="w-4 h-4" aria-hidden="true" />
          Activation risk
        </span>
      </td>
    );
  }
  if (level === "amber") {
    return (
      <td className="px-4 py-3" aria-label="Alert: expiring soon">
        <span className="inline-flex items-center gap-1.5 text-alert-700 text-sm font-medium">
          <ClockIcon className="w-4 h-4" aria-hidden="true" />
          Expiring soon
        </span>
      </td>
    );
  }
  return (
    <td className="px-4 py-3" aria-label="Alert: healthy">
      <span className="inline-flex items-center gap-1.5 text-margin-600 text-sm">
        <CheckCircleIcon className="w-4 h-4" aria-hidden="true" />
        Healthy
      </span>
    </td>
  );
}

/** Column 10 — Extend action button */
export function renderActionsCell(
  member: CohortMember,
  canExtend: boolean,
  onExtend: (tenantId: string) => void,
): React.ReactNode {
  if (!canExtend) {
    return null; // hide-not-disable for unauthorized
  }

  const isNotTrialing = member.stripe_status !== "trialing";

  if (isNotTrialing) {
    return (
      <span
        className="text-sm text-neutral-400 cursor-not-allowed px-1 py-0.5"
        title="Cannot extend — subscription is not trialing"
      >
        Extend
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onExtend(member.tenant_id)}
      className="text-brand-600 text-sm font-medium hover:text-brand-700 hover:underline focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md px-1 py-0.5"
      aria-label={`Extend free period for ${member.business_name}`}
    >
      Extend
    </button>
  );
}
