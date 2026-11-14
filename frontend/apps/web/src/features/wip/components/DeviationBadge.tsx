/**
 * DeviationBadge — 4-variant budget deviation badge (NEW domain component)
 *
 * Location: apps/web/src/features/wip/components/DeviationBadge.tsx
 *
 * Color is NEVER the only signal — every variant pairs icon + text + color (WCAG 1.4.1).
 * The `watch` variant uses the server-computed `below_margin_target` boolean — the badge
 * does NOT re-derive margin logic client-side (spec §2.5, §9.6).
 *
 * Per batch-up-1-ui-design-spec.md §2.5 + Accessibility Notes.
 */

import {
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  ExclamationCircleIcon,
  MinusIcon,
} from "@heroicons/react/24/outline";

export type DeviationVariant = "over" | "under" | "watch" | "none";

interface DeviationBadgeProps {
  /** Budget deviation percentage (null = no quote) */
  budgetDeviationPct: number | null | undefined;
  /** Server-computed: true if projected margin is below the tenant's target */
  belowMarginTarget: boolean;
  /** Tenant margin target percentage (e.g. 20.0) — used for the watch threshold */
  marginTargetPct: number;
}

/**
 * Selects the badge variant from the row's deviation + server flags.
 *
 * Conditions (spec §2.5):
 * - none:  budget_deviation_pct === null (no quote)
 * - over:  deviation < 0 (projected over budget)
 * - watch: deviation >= (100 - margin_target_pct) AND below_margin_target === true
 * - under: 0 <= deviation < (100 - margin_target_pct) (healthy, under budget)
 */
export function selectDeviationVariant(
  deviation: number | null | undefined,
  belowMarginTarget: boolean,
  marginTargetPct: number,
): DeviationVariant {
  if (deviation == null) return "none";
  if (deviation < 0) return "over";
  // deviation >= 0 here
  const watchThreshold = 100 - marginTargetPct;
  if (deviation >= watchThreshold && belowMarginTarget) return "watch";
  return "under";
}

function formatDeviation(deviation: number): string {
  return Math.abs(deviation).toFixed(1);
}

export function DeviationBadge({
  budgetDeviationPct,
  belowMarginTarget,
  marginTargetPct,
}: DeviationBadgeProps) {
  const variant = selectDeviationVariant(
    budgetDeviationPct,
    belowMarginTarget,
    marginTargetPct,
  );

  const badgeBase =
    "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-caption font-medium";

  switch (variant) {
    case "over":
      return (
        <span
          className={`${badgeBase} bg-fault-50 text-fault-700 border border-fault-200`}
          data-testid="deviation-badge-over"
        >
          <ArrowTrendingDownIcon className="w-4 h-4" aria-hidden="true" />
          {formatDeviation(budgetDeviationPct!)}% over
        </span>
      );
    case "under":
      return (
        <span
          className={`${badgeBase} bg-margin-50 text-margin-700 border border-margin-200`}
          data-testid="deviation-badge-under"
        >
          <ArrowTrendingUpIcon className="w-4 h-4" aria-hidden="true" />
          {formatDeviation(budgetDeviationPct!)}% under
        </span>
      );
    case "watch":
      return (
        <span
          className={`${badgeBase} bg-alert-50 text-alert-700 border border-alert-200`}
          data-testid="deviation-badge-watch"
        >
          <ExclamationCircleIcon className="w-4 h-4" aria-hidden="true" />
          {formatDeviation(budgetDeviationPct!)}% under
        </span>
      );
    case "none":
      return (
        <span
          className={`${badgeBase} bg-neutral-100 text-neutral-500 border border-neutral-200`}
          data-testid="deviation-badge-none"
        >
          <MinusIcon className="w-4 h-4" aria-hidden="true" />
          No quote
        </span>
      );
  }
}
