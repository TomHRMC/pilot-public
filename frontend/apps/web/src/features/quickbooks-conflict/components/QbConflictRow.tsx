/**
 * QbConflictRow — single row in the QB conflicts queue table
 *
 * Location: apps/web/src/features/quickbooks-conflict/components/QbConflictRow.tsx
 *
 * Established FE-B9.
 * Tokens (all from pilotPreset — ZERO hex values):
 *   bg-brand-100 text-brand-700   — Invoice pill (highest stakes)
 *   bg-neutral-100 text-neutral-700 — Customer / Quote / Expense pills
 */

"use client";

import React from "react";
import Link from "next/link";
import { ExpiryCountdownBadge } from "@pilot/ui";
import type { QbConflictQueueItem } from "../types";

interface QbConflictRowProps {
  conflict: QbConflictQueueItem;
  testID?: string;
}

const ENTITY_TYPE_PILL: Record<
  QbConflictQueueItem["entityType"],
  { label: string; className: string }
> = {
  invoice: {
    label: "Invoice",
    className: "bg-brand-100 text-brand-700",
  },
  quote: {
    label: "Quote",
    className: "bg-neutral-100 text-neutral-700",
  },
  customer: {
    label: "Customer",
    className: "bg-neutral-100 text-neutral-700",
  },
  expense: {
    label: "Expense",
    className: "bg-neutral-100 text-neutral-700",
  },
};

function formatDollars(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function QbConflictRow({ conflict, testID }: QbConflictRowProps) {
  const pill = ENTITY_TYPE_PILL[conflict.entityType];

  return (
    <tr
      className="border-b border-neutral-200 hover:bg-neutral-50"
      data-testid={testID ?? `qb-conflict-row-${conflict.id}`}
    >
      {/* Entity name + display */}
      <td className="px-4 py-3">
        <span className="text-body font-medium text-neutral-900">
          {conflict.entityDisplayName}
        </span>
      </td>

      {/* Entity type pill */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2 py-1 text-caption font-medium ${pill.className}`}
            data-testid={`entity-type-pill-${conflict.entityType}`}
          >
            {pill.label}
          </span>
          {conflict.daysUntilExpiry !== null && (
            <ExpiryCountdownBadge daysUntilExpiry={conflict.daysUntilExpiry} />
          )}
        </div>
      </td>

      {/* Financial delta (invoice only) */}
      <td className="px-4 py-3">
        {conflict.financialDeltaCents !== null ? (
          <span className="text-caption font-medium text-alert-700">
            {formatDollars(Math.abs(conflict.financialDeltaCents))} delta
          </span>
        ) : (
          <span className="text-caption text-neutral-400">—</span>
        )}
      </td>

      {/* Detection date */}
      <td className="px-4 py-3">
        <span className="text-caption text-neutral-600">
          {formatDate(conflict.detectedAt)}
        </span>
      </td>

      {/* Action */}
      <td className="px-4 py-3">
        <Link
          href={`/settings/integrations/quickbooks/conflicts/${conflict.id}`}
          className="text-caption font-medium text-brand-600 hover:text-brand-700 hover:underline"
          data-testid={`resolve-link-${conflict.id}`}
        >
          Resolve →
        </Link>
      </td>
    </tr>
  );
}
