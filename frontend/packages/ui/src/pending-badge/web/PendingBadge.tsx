/**
 * PendingBadge — Web (Tailwind/shadcn) variant
 *
 * Location: packages/ui/src/pending-badge/web/PendingBadge.tsx
 *
 * Renders an optimistic UI pending count badge using Tailwind token classes.
 * Zero count renders null — no visual noise when synced.
 *
 * Token color mapping (NO hardcoded hex values — Tailwind token classes only):
 *   pending  → bg-alert-400 text-alert-900 (amber)
 *   syncing  → bg-brand-400 text-neutral-900 animate-pulse (blue)
 *   failed   → bg-fault-600 text-white (red)
 *   conflict → bg-fault-600 text-white (red)
 *
 * Per batch-fe-b7-design.md Section F.1 and §16.8.
 * ⚠️ ZERO TOLERANCE: No hardcoded colors. Tailwind token classes only.
 */

import React from "react";
import type { PendingBadgeProps, PendingBadgeVariant } from "../types";

const BADGE_CLASSES: Record<PendingBadgeVariant, string> = {
  pending: "bg-alert-400 text-alert-900",
  syncing: "bg-brand-400 text-neutral-900 animate-pulse",
  failed: "bg-fault-600 text-white",
  conflict: "bg-fault-600 text-white",
};

export function PendingBadge({
  count,
  variant = "pending",
  accessibilityLabel,
  testID,
  onPress,
  className = "",
}: PendingBadgeProps): React.ReactElement | null {
  if (count === 0) return null;

  const displayCount = count > 99 ? "99+" : String(count);
  const a11yLabel = accessibilityLabel ?? `${count} pending sync`;
  const variantClasses = BADGE_CLASSES[variant];

  const badgeClasses = [
    "inline-flex items-center justify-center",
    "min-w-[20px] h-5 px-1",
    "rounded-full",
    "text-xs font-medium leading-none",
    variantClasses,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (onPress) {
    return (
      <button
        type="button"
        onClick={onPress}
        className={badgeClasses}
        aria-label={a11yLabel}
        data-testid={testID ?? "pending-badge"}
      >
        {displayCount}
      </button>
    );
  }

  return (
    <span
      className={badgeClasses}
      aria-label={a11yLabel}
      data-testid={testID ?? "pending-badge"}
    >
      {displayCount}
    </span>
  );
}
