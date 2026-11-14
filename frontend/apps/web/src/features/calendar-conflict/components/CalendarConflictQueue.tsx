/**
 * CalendarConflictQueue — paginated conflict list with SSE-driven live updates
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarConflictQueue.tsx
 *
 * Renders the pending conflict table with urgency sort (scheduled_start_at asc).
 * SSE events from useCalendarConflictSse invalidate the cache and trigger refetch.
 * #conflicts anchor for scroll-to targeting from dispatch board.
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

"use client";

import React, { useState } from "react";
import { ErrorState, LoadingState } from "@pilot/ui";
import { CalendarConflictRow } from "./CalendarConflictRow";
import { CalendarEmptyState } from "./CalendarEmptyState";
import { useCalendarConflicts } from "../hooks/useCalendarConflicts";
import { useCalendarConflictSse } from "../hooks/useCalendarConflictSse";
import type { CalendarConflictsParams } from "../types";

interface CalendarConflictQueueProps {
  /** Auto-expiry days setting from tenant config for badge computation */
  autoExpireDays?: number | null;
  testID?: string;
}

export function CalendarConflictQueue({
  autoExpireDays,
  testID,
}: CalendarConflictQueueProps) {
  const [nowMs] = useState(() => Date.now());
  const [statusFilter, setStatusFilter] =
    useState<CalendarConflictsParams["status"]>("pending");
  const [cursor, setCursor] = useState<string | null>(null);

  const params: CalendarConflictsParams = {
    status: statusFilter,
    cursor: cursor ?? undefined,
    limit: 20,
  };

  const { data, isLoading, error, refetch } = useCalendarConflicts(params);

  // Wire SSE channel — cache invalidation happens inside the hook
  useCalendarConflictSse(true);

  if (error) {
    return (
      <ErrorState
        type="network"
        onRetry={() => void refetch()}
        testID="conflict-queue-error"
      />
    );
  }

  const conflicts = data?.conflicts ?? [];
  const nextCursor = data?.nextCursor ?? null;
  const totalPending = data?.totalPending ?? 0;

  return (
    <section
      id="conflicts"
      data-testid={testID ?? "calendar-conflict-queue"}
      className="space-y-4"
      aria-label="Pending calendar conflicts"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-h2 font-medium text-neutral-900">
            Sync Conflicts
          </h2>
          {totalPending > 0 && (
            <p className="text-caption text-neutral-600">
              {totalPending} pending conflict{totalPending === 1 ? "" : "s"}
            </p>
          )}
        </div>

        {/* Status filter */}
        <div className="flex gap-2">
          {(["pending", "resolved", "all"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setStatusFilter(s);
                setCursor(null);
              }}
              className={`rounded-md px-3 py-1.5 text-caption font-medium capitalize focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1 ${
                statusFilter === s
                  ? "bg-brand-600 text-white"
                  : "border border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50"
              }`}
              data-testid={`filter-${s}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <LoadingState type="inline" testID="conflict-queue-loading" />
      ) : conflicts.length === 0 ? (
        <CalendarEmptyState lastSuccessfulSyncAt={null} />
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <table className="w-full text-left" data-testid="conflict-table">
            <thead className="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-caption font-medium text-neutral-700">
                  Job / Event
                </th>
                <th className="px-4 py-3 text-caption font-medium text-neutral-700">
                  Type
                </th>
                <th className="px-4 py-3 text-caption font-medium text-neutral-700">
                  Pilot Modified
                </th>
                <th className="px-4 py-3 text-caption font-medium text-neutral-700">
                  Calendar Modified
                </th>
                <th className="px-4 py-3 text-right text-caption font-medium text-neutral-700">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {conflicts.map((conflict) => {
                // Compute days until expiry if autoExpireDays is set
                let daysUntilExpiry: number | null = null;
                if (autoExpireDays != null) {
                  const detectedMs = new Date(conflict.detectedAt).getTime();
                  const expiresMs =
                    detectedMs + autoExpireDays * 24 * 60 * 60 * 1000;
                  daysUntilExpiry = Math.ceil(
                    (expiresMs - nowMs) / (24 * 60 * 60 * 1000),
                  );
                }

                return (
                  <CalendarConflictRow
                    key={conflict.id}
                    conflict={conflict}
                    daysUntilExpiry={daysUntilExpiry}
                  />
                );
              })}
            </tbody>
          </table>

          {/* Pagination */}
          {(nextCursor || cursor) && (
            <div className="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
              <button
                type="button"
                disabled={!cursor}
                onClick={() => setCursor(null)}
                className="rounded-md border border-neutral-200 px-3 py-1.5 text-caption text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                data-testid="pagination-prev"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!nextCursor}
                onClick={() => setCursor(nextCursor)}
                className="rounded-md border border-neutral-200 px-3 py-1.5 text-caption text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                data-testid="pagination-next"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
