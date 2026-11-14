/**
 * PendingBadge — Shared Types
 *
 * Location: packages/ui/src/pending-badge/types.ts
 *
 * Established in FE-B7. Consumed by FE-B9 (background sync) and
 * FE-B12 (account settings async ops) without changes.
 *
 * ⚠️ Interface locked — changes require FE-B9 and FE-B12 impact review.
 *
 * Per batch-fe-b7-design.md Section F.1 and §16.8 Optimistic UI.
 *
 * Color semantics for sync state indicators:
 *   pending  → $alert-400 amber (queued, awaiting sync)
 *   syncing  → $brand-600 blue, animated pulse (in flight)
 *   failed   → $fault-600 red (failed; retry/resolve CTA available)
 *   conflict → $fault-600 red (conflict requiring action)
 */

export type PendingBadgeVariant =
  | "pending" // amber — queued, awaiting sync
  | "syncing" // amber pulse — actively in flight
  | "failed" // red — failed; retry/resolve CTA available
  | "conflict"; // red — conflict requiring action

export interface PendingBadgeProps {
  /** Number of pending operations on this entity. 0 renders nothing (null). */
  count: number;
  /** Visual state determines color and animation. Defaults to 'pending'. */
  variant?: PendingBadgeVariant;
  /** Accessible label for screen readers. Defaults to "{count} pending sync" */
  accessibilityLabel?: string;
  /** Mobile: testID for Maestro targeting */
  testID?: string;
  /** Optional tap handler — typically opens sync queue drawer */
  onPress?: () => void;
  /** Web: additional Tailwind classes */
  className?: string;
}
