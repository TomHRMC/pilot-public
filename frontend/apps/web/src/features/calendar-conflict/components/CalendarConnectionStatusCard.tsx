/**
 * CalendarConnectionStatusCard — calendar sync connection status display
 *
 * Location: apps/web/src/features/calendar-conflict/components/CalendarConnectionStatusCard.tsx
 *
 * Renders one of four states:
 *   connected   → green dot + "Calendar sync · Last synced X min ago"
 *   syncing     → pulsing amber dot + "Calendar sync · Syncing…"
 *   error       → red dot + reconnect button + NotificationBanner
 *   disconnected → neutral dot + "Calendar not connected" + Connect button
 *
 * Token mapping (all from pilotPreset — zero hardcoded colors):
 *   connected dot: bg-margin-400
 *   conflicts dot: bg-alert-400
 *   error dot:     bg-fault-600
 *   error banner:  bg-fault-50 border-fault-200
 *
 * Pattern ref: design doc batch-fe-b8-design.md §E.3
 */

"use client";

import React from "react";
import type { CalendarConnectionStatus } from "@pilot/ui";

interface CalendarConnectionStatusCardProps {
  status: CalendarConnectionStatus | undefined;
  isLoading: boolean;
  onReconnect?: () => void;
  onConnect?: () => void;
  testID?: string;
}

function formatLastSync(lastSuccessfulSyncAt: string | null): string {
  if (!lastSuccessfulSyncAt) return "Never synced";

  const syncDate = new Date(lastSuccessfulSyncAt);
  const now = new Date();
  const diffMs = now.getTime() - syncDate.getTime();
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}

export function CalendarConnectionStatusCard({
  status,
  isLoading,
  onReconnect,
  onConnect,
  testID,
}: CalendarConnectionStatusCardProps) {
  if (isLoading) {
    return (
      <div
        data-testid={testID ?? "calendar-connection-status-card"}
        className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white p-4"
      >
        <div className="h-3 w-3 animate-pulse rounded-full bg-neutral-300" />
        <span className="text-body text-neutral-400">
          Loading calendar status…
        </span>
      </div>
    );
  }

  if (
    !status ||
    status.connectionStatus === "disconnected" ||
    !status.isConnected
  ) {
    return (
      <div
        data-testid={testID ?? "calendar-connection-status-card"}
        className="flex items-center justify-between gap-4 rounded-lg border border-neutral-200 bg-white p-4"
      >
        <div className="flex items-center gap-3">
          <div
            className="h-3 w-3 flex-shrink-0 rounded-full bg-neutral-300"
            aria-hidden="true"
            data-testid="calendar-status-dot-disconnected"
          />
          <div>
            <p className="text-body font-medium text-neutral-900">
              Calendar sync
            </p>
            <p className="text-caption text-neutral-600">
              No calendar connected
            </p>
          </div>
        </div>
        {onConnect && (
          <button
            type="button"
            onClick={onConnect}
            className="rounded-md bg-brand-600 px-3 py-1.5 text-caption font-medium text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
            data-testid="calendar-connect-btn"
          >
            Connect calendar
          </button>
        )}
      </div>
    );
  }

  const isError =
    status.requiresReconnect || status.connectionStatus === "error";
  const isSyncing = status.connectionStatus === "syncing";
  const hasPendingConflicts = status.pendingConflictsCount > 0;

  let dotClass: string;
  let statusLabel: string;
  let subtitleText: string;

  if (isError) {
    dotClass = "bg-fault-600";
    statusLabel = "Calendar sync · Reconnect needed";
    subtitleText =
      "Sync is paused. Reconnect to resume automatic conflict push.";
  } else if (isSyncing) {
    dotClass = "bg-alert-400 animate-pulse";
    statusLabel = "Calendar sync · Syncing…";
    subtitleText = `Last synced: ${formatLastSync(status.lastSuccessfulSyncAt)}`;
  } else if (hasPendingConflicts) {
    dotClass = "bg-alert-400";
    statusLabel = `Calendar sync · ${status.pendingConflictsCount} conflict${status.pendingConflictsCount === 1 ? "" : "s"} pending`;
    subtitleText = `Last synced: ${formatLastSync(status.lastSuccessfulSyncAt)}`;
  } else {
    dotClass = "bg-margin-400";
    statusLabel = "Calendar sync · Up to date";
    subtitleText = `Last synced: ${formatLastSync(status.lastSuccessfulSyncAt)}`;
  }

  return (
    <div
      data-testid={testID ?? "calendar-connection-status-card"}
      className="space-y-3"
    >
      {/* Error reconnect banner */}
      {isError && (
        <div
          className="flex items-center gap-2 rounded-md border border-fault-200 bg-fault-50 px-4 py-3"
          role="alert"
          data-testid="calendar-error-banner"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4 flex-shrink-0 text-fault-600"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
              clipRule="evenodd"
            />
          </svg>
          <p className="text-caption text-fault-700">
            Sync error blocking automatic conflict push — reconnect to resume.
          </p>
        </div>
      )}

      {/* Status row */}
      <div className="flex items-center justify-between gap-4 rounded-lg border border-neutral-200 bg-white p-4">
        <div className="flex items-center gap-3">
          <div
            className={`h-3 w-3 flex-shrink-0 rounded-full ${dotClass}`}
            aria-hidden="true"
            data-testid={`calendar-status-dot-${isError ? "error" : isSyncing ? "syncing" : hasPendingConflicts ? "conflicts" : "connected"}`}
          />
          <div>
            <p className="text-body font-medium text-neutral-900">
              {statusLabel}
            </p>
            <p className="text-caption text-neutral-600">{subtitleText}</p>
          </div>
        </div>

        {isError && onReconnect && (
          <button
            type="button"
            onClick={onReconnect}
            className="rounded-md bg-brand-600 px-3 py-1.5 text-caption font-medium text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
            data-testid="calendar-reconnect-btn"
          >
            Reconnect
          </button>
        )}
      </div>
    </div>
  );
}
