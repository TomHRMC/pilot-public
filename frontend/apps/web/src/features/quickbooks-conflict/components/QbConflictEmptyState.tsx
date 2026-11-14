/**
 * QbConflictEmptyState — empty state for QB conflicts queue
 *
 * Location: apps/web/src/features/quickbooks-conflict/components/QbConflictEmptyState.tsx
 *
 * Established FE-B9.
 * Tokens: text-margin-600 (healthy), text-neutral-600 (meta)
 */

"use client";

import React from "react";

interface QbConflictEmptyStateProps {
  lastSyncedAt?: string | null;
  testID?: string;
}

export function QbConflictEmptyState({
  lastSyncedAt,
  testID,
}: QbConflictEmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-16 text-center"
      data-testid={testID ?? "qb-conflict-empty-state"}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-margin-100">
        <svg
          className="h-6 w-6 text-margin-600"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>
      <h3 className="text-body font-medium text-margin-600">
        No QuickBooks conflicts.
      </h3>
      <p className="max-w-sm text-caption text-neutral-600">
        Your data is in sync.
      </p>
      {lastSyncedAt && (
        <p className="text-caption text-neutral-600">
          Last synced{" "}
          {new Date(lastSyncedAt).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      )}
    </div>
  );
}
