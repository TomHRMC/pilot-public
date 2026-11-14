/**
 * ExpiryCountdownBadge — shows auto-expiry countdown
 *
 * Location: packages/ui/src/integration-conflict-resolver/ExpiryCountdownBadge.tsx
 *
 * Renders an amber badge for > 3 days, red for <= 3 days.
 * Renders nothing when daysUntilExpiry is null/undefined.
 *
 * Color thresholds:
 *   > 3 days → bg-alert-50 border-alert-200 text-alert-600
 *   ≤ 3 days → bg-fault-50 border-fault-200 text-fault-600
 *
 * Token source: tokens.ts ramps: alert, fault.
 * Zero hardcoded hex values or pixel values.
 */

import React from "react";
import type { ExpiryCountdownBadgeProps } from "./types";

/** Days at which the badge escalates from amber to red urgency */
const EXPIRY_URGENT_THRESHOLD_DAYS = 3;

export function ExpiryCountdownBadge({
  daysUntilExpiry,
  testID,
}: ExpiryCountdownBadgeProps) {
  if (daysUntilExpiry === null || daysUntilExpiry === undefined) {
    return null;
  }

  const isUrgent = daysUntilExpiry <= EXPIRY_URGENT_THRESHOLD_DAYS;

  const className = isUrgent
    ? "bg-fault-50 border border-fault-200 text-fault-600"
    : "bg-alert-50 border border-alert-200 text-alert-600";

  const label =
    daysUntilExpiry === 0
      ? "Auto-resolves today"
      : daysUntilExpiry === 1
        ? "Auto-resolves in 1 day"
        : `Auto-resolves in ${daysUntilExpiry} days`;

  return (
    <span
      data-testid={testID ?? "expiry-countdown-badge"}
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-caption font-medium whitespace-nowrap ${className}`}
      role="status"
      aria-label={label}
    >
      {label}
    </span>
  );
}
