/**
 * CalendarConflictRow — single row in the conflict queue table
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarConflictRow.tsx
 *
 * Renders: event title, conflict type pill, Pilot change summary,
 * calendar change summary, job link, ExpiryCountdownBadge, Resolve button.
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

"use client";

import React from "react";
import Link from "next/link";
import { ConflictTypeLabel, ExpiryCountdownBadge } from "@pilot/ui";
import type { CalendarConflictQueueItem } from "../types";

interface CalendarConflictRowProps {
  conflict: CalendarConflictQueueItem;
  /** Days until expiry — computed by parent from tenant settings */
  daysUntilExpiry?: number | null;
  testID?: string;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function CalendarConflictRow({
  conflict,
  daysUntilExpiry,
  testID,
}: CalendarConflictRowProps) {
  const showExpiry =
    daysUntilExpiry !== null &&
    daysUntilExpiry !== undefined &&
    daysUntilExpiry <= 7;

  return (
    <tr
      data-testid={testID ?? `conflict-row-${conflict.id}`}
      className="border-b border-neutral-200 hover:bg-neutral-50"
    >
      {/* Job / event title */}
      <td className="px-4 py-3">
        <div className="space-y-1">
          <p className="text-body font-medium text-neutral-900">
            {conflict.jobTitle ?? "Untitled Job"}
          </p>
          <p className="text-caption text-neutral-600">
            {formatDateTime(conflict.scheduledStartAt)}
          </p>
        </div>
      </td>

      {/* Conflict type pill + expiry badge */}
      <td className="px-4 py-3">
        <div className="flex flex-col gap-1">
          <ConflictTypeLabel conflictType={conflict.conflictType} />
          {showExpiry && (
            <ExpiryCountdownBadge
              daysUntilExpiry={daysUntilExpiry}
              testID={`expiry-badge-${conflict.id}`}
            />
          )}
        </div>
      </td>

      {/* Pilot modified */}
      <td className="px-4 py-3">
        <p className="text-caption text-neutral-700">
          {formatDateTime(conflict.pilotModifiedAt)}
        </p>
      </td>

      {/* Calendar modified */}
      <td className="px-4 py-3">
        <p className="text-caption text-neutral-700">
          {formatDateTime(conflict.externalModifiedAt)}
        </p>
      </td>

      {/* Resolve action */}
      <td className="px-4 py-3 text-right">
        <Link
          href={`/settings/integrations/calendar/conflicts/${conflict.id}`}
          className="rounded-md bg-brand-600 px-3 py-1.5 text-caption font-medium text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
          data-testid={`resolve-link-${conflict.id}`}
        >
          Resolve
        </Link>
      </td>
    </tr>
  );
}
