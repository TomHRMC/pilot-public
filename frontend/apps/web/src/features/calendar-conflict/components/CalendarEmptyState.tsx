/**
 * CalendarEmptyState — empty state for zero pending conflicts
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarEmptyState.tsx
 *
 * Renders "No sync conflicts." + last sync timestamp.
 * Collapsible <CalendarSyncActivityLog> is rendered below.
 *
 * Tokens:
 *   "No sync conflicts" text: text-margin-600 (green = healthy)
 *   timestamp: text-neutral-600
 */

"use client";

import React from "react";

interface CalendarEmptyStateProps {
  lastSuccessfulSyncAt: string | null;
  testID?: string;
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "Never";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? "" : "s"} ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hour${diffHr === 1 ? "" : "s"} ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
}

export function CalendarEmptyState({
  lastSuccessfulSyncAt,
  testID,
}: CalendarEmptyStateProps) {
  return (
    <div
      data-testid={testID ?? "calendar-empty-state"}
      className="flex flex-col items-center justify-center gap-2 py-12 text-center"
    >
      {/* Checkmark icon */}
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-margin-50">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-6 w-6 text-margin-600"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
            clipRule="evenodd"
          />
        </svg>
      </div>

      <p
        className="text-body-lg font-medium text-margin-600"
        data-testid="empty-state-no-conflicts-text"
      >
        No sync conflicts.
      </p>

      <p
        className="text-caption text-neutral-600"
        data-testid="empty-state-last-sync-text"
      >
        Last successful sync:{" "}
        <span className="font-medium">
          {formatRelativeTime(lastSuccessfulSyncAt)}
        </span>
      </p>
    </div>
  );
}
