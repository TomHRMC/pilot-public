/**
 * Tier Picker Card — Types
 * Location: packages/ui/src/tier-picker-card/types.ts
 * Web-only component (signup wizard is web-only; FE-B13 fleshes out).
 *
 * FE-B13: Extended TierName union + additive optional props.
 *         INTERFACE FROZEN after FE-B13. Required props must not change signature.
 */

export interface TierFeature {
  label: string;
  /** When true, feature is included. When false, feature is grayed-out with strikethrough. */
  included: boolean;
  /** Optional callout (e.g., "Unlimited", "Up to 5") */
  callout?: string;
}

/**
 * Extended TierName union — FE-B13 adds 'professional' and 'enterprise'.
 * 'growth' and 'pro' kept for FE-B1 backward compatibility.
 * Open string extension for future DB-driven tiers.
 */
export type TierName =
  | "trial"
  | "starter"
  | "professional"
  | "enterprise"
  | "growth" // kept for FE-B1 backward compat
  | "pro" // kept for FE-B1 backward compat
  | (string & {}); // open extension for future DB-driven tiers

export interface TierPickerCardProps {
  tierName: TierName;
  /** Display name (e.g., "Starter", "Growth Plan") */
  displayName: string;
  /** Monthly price in cents (e.g., 14900 = $149) */
  monthlyPriceCents: number;
  /** Annual price in cents, if applicable */
  annualPriceCents?: number;
  /** Array of feature line items */
  features: TierFeature[];
  /**
   * When true, renders the card with a highlighted/featured treatment.
   * Renders a "Recommended" badge (or recommendedBadgeLabel override).
   */
  isFeatured?: boolean;
  /**
   * When true, this card is the currently selected tier.
   * Applies a border + checkmark treatment.
   */
  isSelected?: boolean;
  onSelect: (tierName: TierName) => void;
  /** CTA label override (default: "Select {displayName}") */
  ctaLabel?: string;
  testID?: string;
  className?: string;
  // ── FE-B13 additive optional props (backward-compatible) ──────────────────
  /**
   * When true: renders "FREE / for {N} days" instead of the formatted cents price.
   * Use with trialDurationDays for trial tier display.
   */
  isTrialTier?: boolean;
  /** Trial duration in days — shown as "FREE for {N} days" when isTrialTier=true */
  trialDurationDays?: number;
  /**
   * Max user count — rendered as "Up to {N} users" in the feature list
   * as a synthetic feature row when provided.
   */
  maxUsers?: number;
  /**
   * When true: renders "(current)" label instead of the CTA button.
   * Card is still visible but not selectable (for conversion context).
   */
  isCurrentTier?: boolean;
  /**
   * Override text for the "Recommended" badge.
   * Defaults to "Recommended" when isFeatured=true.
   */
  recommendedBadgeLabel?: string;
}

/**
 * TierPickerCardPropsExtended — alias for component consumers who want
 * the full extended props type explicitly.
 * @deprecated Use TierPickerCardProps directly — FE-B13 merged extensions in.
 */
export type TierPickerCardPropsExtended = TierPickerCardProps;
