/**
 * CalendarSyncActivityLog — collapsible last-N sync events
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarSyncActivityLog.tsx
 *
 * Renders when no pending conflicts (spec Decision 12 empty state).
 * Shows last 10 sync events in a collapsible accordion.
 *
 * Tokens: all from pilotPreset — zero hardcoded colors.
 */

"use client";

import React, { useState } from "react";

interface SyncActivityItem {
  id: string;
  eventType: string;
  occurredAt: string;
  description: string;
  status: "success" | "warning" | "error";
}

interface CalendarSyncActivityLogProps {
  activities?: SyncActivityItem[];
  isLoading?: boolean;
  testID?: string;
}

const STATUS_CLASS: Record<SyncActivityItem["status"], string> = {
  success: "text-margin-600",
  warning: "text-alert-600",
  error: "text-fault-600",
};

const STATUS_DOT: Record<SyncActivityItem["status"], string> = {
  success: "bg-margin-400",
  warning: "bg-alert-400",
  error: "bg-fault-600",
};

export function CalendarSyncActivityLog({
  activities = [],
  isLoading = false,
  testID,
}: CalendarSyncActivityLogProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <section
      data-testid={testID ?? "calendar-sync-activity-log"}
      className="rounded-lg border border-neutral-200 bg-white"
    >
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-600"
        aria-expanded={isExpanded}
        data-testid="activity-log-toggle"
      >
        <span className="text-body font-medium text-neutral-900">
          Recent Sync Activity
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 text-neutral-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isExpanded && (
        <div
          className="border-t border-neutral-200 px-4 pb-4 pt-2"
          data-testid="activity-log-content"
        >
          {isLoading && (
            <p className="py-3 text-caption text-neutral-400">
              Loading activity…
            </p>
          )}

          {!isLoading && activities.length === 0 && (
            <p className="py-3 text-caption text-neutral-500">
              No recent sync activity.
            </p>
          )}

          {!isLoading && activities.length > 0 && (
            <ul className="divide-y divide-neutral-100" role="list">
              {activities.map((item) => (
                <li key={item.id} className="flex items-center gap-3 py-2">
                  <div
                    className={`h-2 w-2 flex-shrink-0 rounded-full ${STATUS_DOT[item.status]}`}
                    aria-hidden="true"
                  />
                  <div className="flex flex-1 items-center justify-between gap-2">
                    <p className={`text-caption ${STATUS_CLASS[item.status]}`}>
                      {item.description}
                    </p>
                    <time
                      dateTime={item.occurredAt}
                      className="flex-shrink-0 text-caption text-neutral-400"
                    >
                      {new Date(item.occurredAt).toLocaleTimeString(undefined, {
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </time>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
