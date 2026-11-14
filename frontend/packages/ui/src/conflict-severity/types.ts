/**
 * ConflictSeverity — Shared Types & Visual Token Mapping
 *
 * Location: packages/ui/src/conflict-severity/types.ts
 * Exported from: packages/ui/src/index.ts
 *
 * Established in FE-B4 (dispatch board).
 * Consumed by FE-B7 (offline sync), FE-B8 (calendar), FE-B9 (QB).
 *
 * Per mvp-arch.md §13.4 (four-class severity) and §16.6 (visual treatment).
 *
 * ⚠️ INTERFACE LOCKED — CONFLICT_CLASS_TOKENS must not be redefined in
 * consuming batches. Import and use directly.
 */

/** Per mvp-arch.md §13.4 — dispatch conflict classification */
export type DispatchConflictClass =
  | "overlap"
  | "availability"
  | "travel"
  | "info";

/** Per mvp-arch.md §16.6 — four-tier severity routing */
export type FourClassSeverity = "block" | "warn" | "info";

/** Visual token keys for each conflict class (resolve to Pass 1 tokens) */
export interface ConflictVisualTokens {
  /** Tailwind class for the badge background color */
  badgeBgClass: string;
  /** Tailwind class for the badge text color */
  badgeTextClass: string;
  /** Display label for the badge */
  badgeText: string;
  /** Banner variant for NotificationBanner */
  bannerVariant: "error" | "warning" | "info" | "neutral";
  /** Tailwind class for banner background */
  bannerBgClass: string;
  /** Tailwind class for banner border */
  bannerBorderClass: string;
  /** Tailwind class for banner text */
  bannerTextClass: string;
  /** Icon name from Pass 1 icon system */
  iconName: string;
  /**
   * Whether drag snap-back occurs.
   * MVP: all false per §13.4 — block severity reserved for Phase 2 strict_mode.
   */
  isBlocking: boolean;
}

/**
 * Canonical visual token mapping for the four dispatch conflict classes.
 * Uses Pass 1 Tailwind token classes only — no hardcoded hex values.
 *
 * @example
 * const tokens = CONFLICT_CLASS_TOKENS['overlap'];
 * <span className={`${tokens.badgeBgClass} ${tokens.badgeTextClass}`}>
 *   {tokens.badgeText}
 * </span>
 */
export const CONFLICT_CLASS_TOKENS: Record<
  DispatchConflictClass,
  ConflictVisualTokens
> = {
  overlap: {
    badgeBgClass: "bg-fault-50",
    badgeTextClass: "text-fault-600",
    badgeText: "Overlap",
    bannerVariant: "error",
    bannerBgClass: "bg-fault-50",
    bannerBorderClass: "border-fault-200",
    bannerTextClass: "text-fault-600",
    iconName: "alert-circle",
    // MVP: warn-only per §13.4; block available Phase 2
    isBlocking: false,
  },
  availability: {
    badgeBgClass: "bg-alert-50",
    badgeTextClass: "text-alert-600",
    badgeText: "Availability",
    bannerVariant: "warning",
    bannerBgClass: "bg-alert-50",
    bannerBorderClass: "border-alert-200",
    bannerTextClass: "text-alert-600",
    iconName: "clock",
    isBlocking: false,
  },
  travel: {
    badgeBgClass: "bg-alert-50",
    badgeTextClass: "text-alert-600",
    badgeText: "Drive time",
    bannerVariant: "warning",
    bannerBgClass: "bg-alert-50",
    bannerBorderClass: "border-alert-200",
    bannerTextClass: "text-alert-600",
    iconName: "map-pin",
    isBlocking: false,
  },
  info: {
    badgeBgClass: "bg-neutral-100",
    badgeTextClass: "text-neutral-600",
    badgeText: "Note",
    bannerVariant: "neutral",
    bannerBgClass: "bg-neutral-50",
    bannerBorderClass: "border-neutral-200",
    bannerTextClass: "text-neutral-600",
    iconName: "info",
    isBlocking: false,
  },
} as const;
