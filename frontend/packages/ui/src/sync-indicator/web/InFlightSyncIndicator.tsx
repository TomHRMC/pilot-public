/**
 * InFlightSyncIndicator — Web (unified FE-B15)
 *
 * Location: packages/ui/src/sync-indicator/web/InFlightSyncIndicator.tsx
 *
 * FE-B1: Skeleton implementation.
 * FE-B15 changes:
 *   - Wire onResolve: clickable wrapper in error + synced-pending states
 *   - Fix pending count badge: bg-neutral-200 → bg-alert-100 text-alert-800
 *   - Extend lastSyncedAt display to synced-pending state
 *   - Finalize state label copy (spec-accurate relative times)
 *   - Add hover detail tooltip with pendingItems (capped at 5)
 *   - Respect manualTriggerSupported from hook (replaces hard-coded surface check)
 *
 * Token mapping (H section of batch-fe-b15-design.md):
 *   idle (0 pending)               → bg-margin-400 dot
 *   synced-pending (≤ threshold)   → bg-margin-400 dot  + bg-alert-100 text-alert-800 badge
 *   synced-pending (> threshold)   → bg-alert-400 dot   + bg-alert-100 text-alert-800 badge
 *   syncing                        → bg-alert-400 animate-pulse + bg-alert-100 text-alert-800 badge
 *   error                          → bg-fault-600 dot   + bg-fault-100 text-fault-700 badge
 *   paused                         → bg-neutral-400 dot + bg-neutral-100 text-neutral-600 badge
 */

"use client";

import React, { useState } from "react";
import type {
  InFlightSyncIndicatorProps,
  SyncState,
  PendingItem,
} from "../types";

// ─── Dot color ────────────────────────────────────────────────────────────────

function getDotClass(
  state: SyncState,
  pendingCount: number,
  amberThreshold: number,
): string {
  switch (state) {
    case "idle":
      return "bg-margin-400";
    case "syncing":
      return "bg-alert-400 animate-pulse";
    case "error":
      return "bg-fault-600";
    case "paused":
      return "bg-neutral-400";
    case "synced-pending":
      return pendingCount >= amberThreshold ? "bg-alert-400" : "bg-margin-400";
    default:
      return "bg-neutral-300";
  }
}

// ─── Badge classes ─────────────────────────────────────────────────────────────

function getBadgeClass(state: SyncState): string {
  switch (state) {
    case "error":
      return "bg-fault-100 text-fault-700";
    case "paused":
      return "bg-neutral-100 text-neutral-600";
    default:
      return "bg-alert-100 text-alert-800";
  }
}

// ─── State label copy ─────────────────────────────────────────────────────────

function formatRelativeTime(date: Date): string {
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1_000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h ago`;
}

function formatTimeUntil(date: Date): string {
  const diffMs = date.getTime() - Date.now();
  if (diffMs <= 0) return "now";
  const diffSec = Math.floor(diffMs / 1_000);
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h`;
}

function getStateLabel(
  state: SyncState,
  pendingCount: number,
  lastSyncedAt?: Date,
  nextSyncAt?: Date,
): string {
  switch (state) {
    case "idle": {
      // With timestamp: "Synced · last Xs ago" (FE-B15 spec)
      // Without timestamp: "In sync" (backward-compat with FE-B4/B8/B9 prior tests)
      if (lastSyncedAt) {
        return `Synced · last ${formatRelativeTime(lastSyncedAt)}`;
      }
      return "In sync";
    }
    case "synced-pending": {
      const timeStr = nextSyncAt
        ? ` · syncing in ${formatTimeUntil(nextSyncAt)}`
        : "";
      return `Synced · ${pendingCount} pending${timeStr}`;
    }
    case "syncing":
      return pendingCount > 0
        ? `Syncing ${pendingCount} change${pendingCount === 1 ? "" : "s"}…`
        : "Syncing…";
    case "error":
      return pendingCount > 0
        ? `Sync error · ${pendingCount} pending`
        : "Sync error";
    case "paused":
      return pendingCount > 0
        ? `Paused · ${pendingCount} queued`
        : "Sync paused";
    default:
      return "Unknown";
  }
}

// ─── Tooltip ───────────────────────────────────────────────────────────────────

interface PendingTooltipProps {
  pendingItems: PendingItem[];
  pendingCount: number;
}

function PendingTooltip({ pendingItems, pendingCount }: PendingTooltipProps) {
  const shown = pendingItems.slice(0, 5);
  const overflow = pendingCount - shown.length;

  return (
    <div
      role="tooltip"
      className="absolute right-0 top-full mt-1 z-50 min-w-48 max-w-72 rounded-md border border-neutral-200 bg-white shadow-lg py-2 px-3"
    >
      <ul className="space-y-1 text-xs text-neutral-700">
        {shown.map((item, idx) => (
          <li key={idx} className="flex items-start gap-1.5">
            <span className="mt-0.5 inline-block w-1.5 h-1.5 rounded-full bg-neutral-400 flex-shrink-0" />
            <span>{item.label}</span>
          </li>
        ))}
        {overflow > 0 && (
          <li className="text-neutral-400 italic">+{overflow} more</li>
        )}
      </ul>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * InFlightSyncIndicator (web — unified FE-B15)
 *
 * @example
 * // In dispatch board header (compact, local data):
 * <InFlightSyncIndicator
 *   surface="dispatch"
 *   state="syncing"
 *   pendingCount={3}
 *   compact
 *   onResolve={() => router.push('/schedule#conflicts')}
 * />
 *
 * // Full indicator with hook data:
 * const status = useInFlightSyncStatus("quickbooks");
 * <InFlightSyncIndicator
 *   surface="quickbooks"
 *   {...status}
 *   onResolve={() => router.push('/settings/integrations/quickbooks/conflicts')}
 *   onManualSync={handleManualSync}
 * />
 */
export function InFlightSyncIndicator({
  surface,
  pendingCount = 0,
  lastSyncedAt,
  state = "idle",
  amberThreshold = 5,
  onManualSync,
  manualTriggerSupported = true,
  compact = false,
  onResolve,
  pendingItems = [],
  nextSyncAt,
  testID,
}: InFlightSyncIndicatorProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  const dotClass = getDotClass(state, pendingCount, amberThreshold);
  const badgeClass = getBadgeClass(state);
  const stateLabel = getStateLabel(
    state,
    pendingCount,
    lastSyncedAt,
    nextSyncAt,
  );
  const showBadge = pendingCount > 0;

  // "Sync now" only when synced-pending, handler provided, and backend approves
  const showManualSync =
    state === "synced-pending" &&
    !!onManualSync &&
    manualTriggerSupported !== false &&
    surface !== "mobile-sync" &&
    surface !== "background-sync";

  // Click-to-detail is available in error + synced-pending states
  const isClickable =
    !!onResolve && (state === "error" || state === "synced-pending");

  // Show timestamp in idle and synced-pending states
  const showTimestamp =
    !!lastSyncedAt && (state === "idle" || state === "synced-pending");

  // Show tooltip on hover when there are pending items
  const hasTooltip = pendingItems.length > 0 && !compact;

  // ── Compact mode ──────────────────────────────────────────────────────────

  if (compact) {
    const inner = (
      <div
        data-testid={testID ?? `sync-indicator-${surface}`}
        aria-label={`${surface} sync: ${stateLabel}${showBadge ? `, ${pendingCount} pending` : ""}`}
        className={[
          "inline-flex items-center gap-1",
          isClickable
            ? "cursor-pointer hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
            : "",
        ]
          .join(" ")
          .trim()}
        title={stateLabel}
        onClick={isClickable ? onResolve : undefined}
        onKeyDown={
          isClickable
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") onResolve?.();
              }
            : undefined
        }
        role={isClickable ? "button" : undefined}
        tabIndex={isClickable ? 0 : undefined}
      >
        <span
          className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${dotClass}`}
          aria-hidden="true"
        />
        {showBadge && (
          <span
            className={`inline-flex items-center justify-center min-w-4 h-4 px-1 rounded-full text-xs font-medium tabular-nums ${badgeClass}`}
            aria-label={`${pendingCount} pending`}
          >
            {pendingCount}
          </span>
        )}
      </div>
    );

    return inner;
  }

  // ── Full mode ─────────────────────────────────────────────────────────────

  return (
    <div
      data-testid={testID ?? `sync-indicator-${surface}`}
      aria-label={`${surface} sync: ${stateLabel}${showBadge ? `, ${pendingCount} pending` : ""}`}
      className="relative inline-flex items-center gap-2 text-sm"
      onMouseEnter={() => hasTooltip && setTooltipOpen(true)}
      onMouseLeave={() => setTooltipOpen(false)}
      onFocus={() => hasTooltip && setTooltipOpen(true)}
      onBlur={() => setTooltipOpen(false)}
    >
      {/* Clickable wrapper for error/synced-pending states */}
      <div
        className={[
          "inline-flex items-center gap-2",
          isClickable
            ? "cursor-pointer hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
            : "",
        ]
          .join(" ")
          .trim()}
        onClick={isClickable ? onResolve : undefined}
        onKeyDown={
          isClickable
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") onResolve?.();
              }
            : undefined
        }
        role={isClickable ? "button" : undefined}
        tabIndex={isClickable ? 0 : undefined}
        aria-label={
          isClickable ? `${stateLabel} — click to resolve` : undefined
        }
      >
        {/* Status dot */}
        <span
          className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${dotClass}`}
          aria-hidden="true"
        />

        {/* State label */}
        <span className="text-neutral-600">{stateLabel}</span>
      </div>

      {/* Pending count badge */}
      {showBadge && (
        <span
          className={`inline-flex items-center justify-center min-w-4 h-4 px-1 rounded-full text-xs font-medium tabular-nums ${badgeClass}`}
          aria-label={`${pendingCount} pending`}
        >
          {pendingCount}
        </span>
      )}

      {/* Manual sync link */}
      {showManualSync && (
        <button
          type="button"
          onClick={onManualSync}
          className="text-brand-600 underline hover:text-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1"
          aria-label="Sync now"
        >
          Sync now
        </button>
      )}

      {/* Last synced timestamp — shown in idle and synced-pending */}
      {showTimestamp && (
        <span className="text-neutral-400 text-xs">
          {lastSyncedAt!.toLocaleTimeString()}
        </span>
      )}

      {/* Hover detail tooltip */}
      {hasTooltip && tooltipOpen && (
        <PendingTooltip
          pendingItems={pendingItems}
          pendingCount={pendingCount}
        />
      )}
    </div>
  );
}
