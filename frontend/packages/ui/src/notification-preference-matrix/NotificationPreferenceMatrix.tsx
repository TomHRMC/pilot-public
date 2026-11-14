/**
 * NotificationPreferenceMatrix — Shared component
 *
 * Location: packages/ui/src/notification-preference-matrix/NotificationPreferenceMatrix.tsx
 *
 * Renders the 8×3 (or 9×3 with asymmetric customer activity) notification
 * preference matrix. Composes EffectiveSettingDisplay cells in "cell mode".
 *
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 uses visibleCategories to embed a subset.
 *
 * RULE: Forced-minimum cells (can_disable===false) are semantically non-interactive:
 *   - aria-disabled="true"
 *   - no tabIndex
 *   - pointer-events: none
 *   - lock glyph + tooltip explaining why locked
 *   - bg-neutral-100 text-neutral-400 (per design doc Section H token audit)
 *
 * RULE: No inline save logic — mutations are passed as callbacks.
 * RULE: No hardcoded design values — all tokens from design doc Section H.
 */

"use client";

import React, { useState } from "react";
import type {
  NotificationPreferenceMatrixProps,
  NotificationPreferenceCell,
  NotificationCategoryRow,
  NotificationChannel,
} from "./types";

// ─── Lock icon ────────────────────────────────────────────────────────────────

function LockIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`w-3.5 h-3.5 ${className}`}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Scope badge ──────────────────────────────────────────────────────────────

function ScopeBadge({ scope }: { scope: NotificationPreferenceCell["scope"] }) {
  // Token audit from design doc Section H
  const classes: Record<typeof scope, string> = {
    user: "bg-brand-50 text-brand-700",
    tenant: "bg-neutral-100 text-neutral-600",
    system: "bg-neutral-50 text-neutral-400",
    fallback: "bg-neutral-50 text-neutral-400",
  };
  const labels: Record<typeof scope, string> = {
    user: "you",
    tenant: "tenant",
    system: "default",
    fallback: "default",
  };
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-medium leading-none ${classes[scope]}`}
    >
      {labels[scope]}
    </span>
  );
}

// ─── Forced-minimum cell (non-interactive per RULE 3) ─────────────────────────

function ForcedMinimumCell({
  cell,
  tooltipText,
}: {
  cell: NotificationPreferenceCell;
  tooltipText: string;
}) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className="relative flex items-center justify-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
    >
      {/* Toggle — visually rendered but non-interactive */}
      <div
        role="switch"
        aria-checked={cell.enabled}
        aria-disabled="true"
        aria-label={`${cell.category_id} ${cell.channel} notification (locked)`}
        aria-describedby={`forced-min-tooltip-${cell.category_id}-${cell.channel}`}
        // Non-interactive enforcement: no tabIndex, no pointer events
        className="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full bg-neutral-100 cursor-not-allowed"
        style={{ pointerEvents: "none" }}
        data-testid={`forced-min-cell-${cell.category_id}-${cell.channel}`}
      >
        <span className="inline-block h-3.5 w-3.5 rounded-full bg-neutral-400 translate-x-4 shadow" />
      </div>
      <LockIcon className="ml-1 text-neutral-400 flex-shrink-0" />

      {/* Tooltip */}
      {showTooltip && (
        <div
          id={`forced-min-tooltip-${cell.category_id}-${cell.channel}`}
          role="tooltip"
          className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 z-10 w-48 rounded-md bg-neutral-900 px-2.5 py-1.5 text-xs text-white shadow-lg"
        >
          {tooltipText}
        </div>
      )}
    </div>
  );
}

// ─── Normal cell (interactive toggle) ─────────────────────────────────────────

function NotificationMatrixCell({
  cell,
  isPending,
  onCellChange,
  onCellRevert,
}: {
  cell: NotificationPreferenceCell;
  isPending?: boolean;
  onCellChange: (enabled: boolean) => Promise<void>;
  onCellRevert: () => Promise<void>;
}) {
  const [localEnabled, setLocalEnabled] = useState(cell.enabled);
  const [inlineError, setInlineError] = useState<string | null>(null);

  // Keep in sync with server state
  React.useEffect(() => {
    setLocalEnabled(cell.enabled);
  }, [cell.enabled]);

  const handleToggle = async () => {
    if (isPending) return;
    const next = !localEnabled;
    setLocalEnabled(next); // optimistic
    setInlineError(null);
    try {
      await onCellChange(next);
    } catch (err) {
      // Revert on error
      setLocalEnabled(cell.enabled);
      setInlineError(
        err instanceof Error ? err.message : "Couldn't save preference.",
      );
    }
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex items-center gap-1">
        <button
          role="switch"
          type="button"
          aria-checked={localEnabled}
          aria-label={`${cell.category_id} ${cell.channel} notification`}
          disabled={isPending}
          onClick={handleToggle}
          className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors
            focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1
            disabled:opacity-50
            ${localEnabled ? "bg-brand-600" : "bg-neutral-300"}
          `}
          data-testid={`matrix-cell-${cell.category_id}-${cell.channel}`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
              localEnabled ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {/* Scope badge */}
      <ScopeBadge scope={cell.scope} />

      {/* Per-cell revert (only if user-overridden) */}
      {cell.scope === "user" && (
        <button
          type="button"
          onClick={onCellRevert}
          disabled={isPending}
          className="text-xs text-brand-600 hover:text-brand-800 focus:outline-none focus:underline disabled:opacity-50"
          aria-label={`Revert ${cell.channel} to tenant default`}
        >
          Revert
        </button>
      )}

      {inlineError && (
        <p className="text-xs text-fault-600 max-w-16 text-center leading-tight">
          {inlineError}
        </p>
      )}
    </div>
  );
}

// ─── Category Row ─────────────────────────────────────────────────────────────

const CHANNEL_ORDER: NotificationChannel[] = ["push", "email", "in_app"];
const CHANNEL_LABELS: Record<NotificationChannel, string> = {
  push: "Push",
  email: "Email",
  in_app: "In-app",
};

function getForcedMinTooltip(categoryId: string, channel: NotificationChannel) {
  if (categoryId === "customer_activity" && channel === "push") {
    return "Push for Customer activity can't be turned off when you're the tech in a conversation.";
  }
  if (categoryId === "system_alerts") {
    return "System alerts can't be turned off — they contain critical platform information.";
  }
  return "This notification can't be turned off for your account.";
}

function NotificationCategoryRowComponent({
  category,
  cells,
  isPending,
  onCellChange,
  onCellRevert,
  onRowRevert,
}: {
  category: NotificationCategoryRow;
  cells: NotificationPreferenceCell[];
  isPending?: boolean;
  onCellChange: (
    channel: NotificationChannel,
    enabled: boolean,
  ) => Promise<void>;
  onCellRevert: (channel: NotificationChannel) => Promise<void>;
  onRowRevert: () => Promise<void>;
}) {
  const hasUserOverride = cells.some((c) => c.scope === "user");

  const getCellFor = (channel: NotificationChannel) =>
    cells.find((c) => c.channel === channel);

  return (
    <tr className="border-b border-neutral-100">
      {/* Category label */}
      <td className="py-3 pr-4 text-left">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-neutral-800">
            {category.display_label}
          </span>
          {hasUserOverride && (
            <button
              type="button"
              onClick={onRowRevert}
              disabled={isPending}
              className="text-xs text-brand-600 hover:text-brand-800 focus:outline-none focus:underline disabled:opacity-50 text-left"
              aria-label={`Reset ${category.display_label} to tenant defaults`}
            >
              Match tenant default
            </button>
          )}
        </div>
      </td>

      {/* One cell per channel */}
      {CHANNEL_ORDER.map((channel) => {
        const cell = getCellFor(channel);
        if (!cell) {
          return (
            <td key={channel} className="py-3 px-2 text-center">
              <span className="text-neutral-300 text-xs">—</span>
            </td>
          );
        }

        return (
          <td
            key={channel}
            className="py-3 px-2 text-center"
            data-testid={`matrix-td-${category.category_id}-${channel}`}
          >
            {!cell.can_disable ? (
              <ForcedMinimumCell
                cell={cell}
                tooltipText={getForcedMinTooltip(category.category_id, channel)}
              />
            ) : (
              <NotificationMatrixCell
                cell={cell}
                isPending={isPending}
                onCellChange={(enabled) => onCellChange(channel, enabled)}
                onCellRevert={() => onCellRevert(channel)}
              />
            )}
          </td>
        );
      })}
    </tr>
  );
}

// ─── Main Matrix ──────────────────────────────────────────────────────────────

/**
 * NotificationPreferenceMatrix
 *
 * Renders the 8-category × 3-channel notification preference grid.
 * Each cell composes <EffectiveSettingDisplay> in cell mode (via NotificationMatrixCell).
 * Forced-minimum cells are non-interactive (aria-disabled, no pointer events, no tabIndex).
 *
 * @example
 * <NotificationPreferenceMatrix
 *   preferences={preferences}
 *   categories={categories}
 *   onCellChange={handleCellChange}
 *   onRowRevert={handleRowRevert}
 *   onCellRevert={handleCellRevert}
 *   onMuteAllPush={handleMuteAllPush}
 *   onMuteAllEmail={handleMuteAllEmail}
 *   onResetAll={handleResetAll}
 * />
 */
export function NotificationPreferenceMatrix({
  preferences,
  categories,
  onCellChange,
  onRowRevert,
  onCellRevert,
  onMuteAllPush,
  onMuteAllEmail,
  onResetAll,
  isPending,
  visibleCategories,
  testID,
}: NotificationPreferenceMatrixProps) {
  const filteredCategories = visibleCategories
    ? categories.filter((c) => visibleCategories.includes(c.category_id))
    : categories;

  const sortedCategories = [...filteredCategories].sort(
    (a, b) => a.display_order - b.display_order,
  );

  function getCellsForCategory(categoryId: string) {
    return preferences.filter((p) => p.category_id === categoryId);
  }

  return (
    <div
      data-testid={testID ?? "notification-preference-matrix"}
      className="flex flex-col gap-4"
    >
      {/* Bulk action bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={onMuteAllPush}
          disabled={isPending}
          className="text-sm text-neutral-600 hover:text-neutral-800 border border-neutral-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-neutral-300 disabled:opacity-50"
          data-testid="mute-all-push"
        >
          Mute all push (non-critical)
        </button>
        <button
          type="button"
          onClick={onMuteAllEmail}
          disabled={isPending}
          className="text-sm text-neutral-600 hover:text-neutral-800 border border-neutral-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-neutral-300 disabled:opacity-50"
          data-testid="mute-all-email"
        >
          Mute all email
        </button>
        <button
          type="button"
          onClick={onResetAll}
          disabled={isPending}
          className="text-sm text-neutral-600 hover:text-neutral-800 border border-neutral-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-neutral-300 disabled:opacity-50"
          data-testid="reset-all"
        >
          Reset to tenant defaults
        </button>
      </div>

      {/* Matrix table */}
      <div className="overflow-x-auto rounded-lg border border-neutral-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50">
              <th className="py-3 pr-4 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                Category
              </th>
              {CHANNEL_ORDER.map((channel) => (
                <th
                  key={channel}
                  className="py-3 px-2 text-center text-xs font-semibold text-neutral-500 uppercase tracking-wide"
                >
                  {CHANNEL_LABELS[channel]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedCategories.map((category) => (
              <NotificationCategoryRowComponent
                key={category.category_id}
                category={category}
                cells={getCellsForCategory(category.category_id)}
                isPending={isPending}
                onCellChange={(channel, enabled) =>
                  onCellChange(category.category_id, channel, enabled)
                }
                onCellRevert={(channel) =>
                  onCellRevert(category.category_id, channel)
                }
                onRowRevert={() => onRowRevert(category.category_id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
