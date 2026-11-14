/**
 * FieldIssueRow — single row in the field issues queue table
 *
 * Location: apps/web/src/features/field-issues/components/FieldIssueRow.tsx
 *
 * Established FE-B9. Displays tech, operation type pill, status pill, resolve link.
 * Tokens (all from pilotPreset — ZERO hex values):
 *   bg-alert-100 text-alert-700   — Pending status pill (amber)
 *   bg-margin-100 text-margin-700 — Auto-recovered pill (green)
 *   bg-neutral-100 text-neutral-600 — Stale pill (neutral)
 */

"use client";

import React from "react";
import Link from "next/link";
import type { FieldIssueQueueItem } from "../types";

interface FieldIssueRowProps {
  issue: FieldIssueQueueItem;
  testID?: string;
}

const STATUS_PILL: Record<
  FieldIssueQueueItem["status"],
  { label: string; className: string }
> = {
  pending: {
    label: "Pending",
    className: "bg-alert-100 text-alert-700",
  },
  auto_recovered: {
    label: "Auto-recovered",
    className: "bg-margin-100 text-margin-700",
  },
  stale: {
    label: "Stale",
    className: "bg-neutral-100 text-neutral-600",
  },
};

const OPERATION_ICON: Record<FieldIssueQueueItem["operationType"], string> = {
  time_entry: "⏱",
  expense: "💳",
  photo: "📷",
  status_change: "🔄",
  loto: "🔒",
};

const OPERATION_LABEL: Record<FieldIssueQueueItem["operationType"], string> = {
  time_entry: "Time entry",
  expense: "Expense",
  photo: "Photo",
  status_change: "Status change",
  loto: "LOTO",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function FieldIssueRow({ issue, testID }: FieldIssueRowProps) {
  const status = STATUS_PILL[issue.status];

  return (
    <tr
      className="border-b border-neutral-200 hover:bg-neutral-50"
      data-testid={testID ?? `field-issue-row-${issue.id}`}
    >
      {/* Tech name */}
      <td className="px-4 py-3">
        <span className="text-body font-medium text-neutral-900">
          {issue.techName}
        </span>
      </td>

      {/* Operation type pill */}
      <td className="px-4 py-3">
        <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-1 text-caption text-neutral-700">
          <span aria-hidden="true">{OPERATION_ICON[issue.operationType]}</span>
          {OPERATION_LABEL[issue.operationType]}
        </span>
      </td>

      {/* Issue summary */}
      <td className="px-4 py-3">
        <p className="max-w-xs text-caption text-neutral-600 line-clamp-2">
          {issue.explainerSummary}
        </p>
      </td>

      {/* Captured timestamp */}
      <td className="px-4 py-3">
        <span className="text-caption text-neutral-600">
          {formatDate(issue.capturedAt)}
        </span>
      </td>

      {/* Status pill */}
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2 py-1 text-caption font-medium ${status.className}`}
          data-testid={`status-pill-${issue.status}`}
        >
          {status.label}
        </span>
      </td>

      {/* Resolve action */}
      <td className="px-4 py-3">
        {issue.status === "pending" ? (
          <Link
            href={`/dashboard/approvals/field-issues/${issue.id}`}
            className="text-caption font-medium text-brand-600 hover:text-brand-700 hover:underline"
            data-testid={`resolve-link-${issue.id}`}
          >
            Resolve →
          </Link>
        ) : (
          <Link
            href={`/dashboard/approvals/field-issues/${issue.id}`}
            className="text-caption text-neutral-500 hover:text-neutral-700 hover:underline"
            data-testid={`view-link-${issue.id}`}
          >
            View
          </Link>
        )}
      </td>
    </tr>
  );
}
