/**
 * TierPickerCard — Web-only
 *
 * Location: packages/ui/src/tier-picker-card/TierPickerCard.tsx
 *
 * FE-B1: Full card layout — tier name, price, feature list, CTA.
 *        isFeatured and isSelected visual treatments applied.
 * FE-B13: Fleshed out with trial-specific display, maxUsers, isCurrentTier,
 *         recommendedBadgeLabel. Extended TierName union.
 *         INTERFACE FROZEN after FE-B13 — required props are locked.
 *
 * Token audit (Section H):
 *  - Featured "Recommended" badge: bg-brand-600 text-white (existing)
 *  - Selected border: border-brand-600 (existing)
 *  - Trial "FREE" price text: text-brand-600
 *  - Completed feature checkmark: text-margin-600 (existing)
 */

import React from "react";
import type { TierPickerCardProps } from "./types";

/** Format cents to dollar string — e.g., 14900 → "$149" */
function formatCents(cents: number): string {
  const dollars = Math.floor(cents / 100);
  const remaining = cents % 100;
  if (remaining === 0) return `$${dollars}`;
  return `$${dollars}.${String(remaining).padStart(2, "0")}`;
}

/**
 * TierPickerCard (web)
 *
 * @example FE-B1 minimal usage (still compiles)
 * <TierPickerCard
 *   tierName="growth"
 *   displayName="Growth Plan"
 *   monthlyPriceCents={14900}
 *   features={[{ label: "Voice quoting", included: true }]}
 *   isSelected={selected === "growth"}
 *   onSelect={setSelected}
 * />
 *
 * @example FE-B13 trial tier
 * <TierPickerCard
 *   tierName="trial"
 *   displayName="Free Trial"
 *   monthlyPriceCents={0}
 *   isTrialTier
 *   trialDurationDays={14}
 *   features={[{ label: "Voice quoting", included: true }]}
 *   isFeatured
 *   isSelected={selected === "trial"}
 *   onSelect={setSelected}
 * />
 */
export function TierPickerCard({
  tierName,
  displayName,
  monthlyPriceCents,
  annualPriceCents,
  features,
  isFeatured = false,
  isSelected = false,
  onSelect,
  ctaLabel,
  testID,
  className,
  // FE-B13 extended props
  isTrialTier = false,
  trialDurationDays,
  maxUsers,
  isCurrentTier = false,
  recommendedBadgeLabel = "Recommended",
}: TierPickerCardProps) {
  const resolvedCtaLabel = ctaLabel ?? `Select ${displayName}`;

  // isCurrentTier cards are visible but not selectable
  const handleSelect = () => {
    if (!isCurrentTier) onSelect(tierName);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if ((e.key === "Enter" || e.key === " ") && !isCurrentTier) {
      e.preventDefault();
      onSelect(tierName);
    }
  };

  return (
    <div
      data-testid={testID ?? `tier-picker-card-${tierName}`}
      role="radio"
      aria-checked={isSelected}
      aria-disabled={isCurrentTier || undefined}
      tabIndex={isCurrentTier ? -1 : 0}
      onKeyDown={handleKeyDown}
      className={`
        relative flex flex-col gap-4 rounded-xl border-2 p-6
        transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
        ${isCurrentTier ? "cursor-default opacity-80" : "cursor-pointer"}
        ${
          isSelected
            ? "border-brand-600 bg-brand-50 shadow-md"
            : isFeatured
              ? "border-brand-200 bg-white shadow-sm"
              : "border-neutral-200 bg-white"
        }
        ${className ?? ""}
      `}
      onClick={handleSelect}
    >
      {/* Featured / Recommended badge */}
      {isFeatured && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold bg-brand-600 text-white">
            {recommendedBadgeLabel}
          </span>
        </div>
      )}

      {/* Selected checkmark (only when not isCurrentTier) */}
      {isSelected && !isCurrentTier && (
        <div className="absolute top-4 right-4">
          <div className="w-5 h-5 rounded-full bg-brand-600 flex items-center justify-center">
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              viewBox="0 0 12 12"
              aria-hidden="true"
            >
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>
      )}

      {/* Header: tier name + price */}
      <div className="flex flex-col gap-1">
        <h3 className="text-h3 font-semibold text-neutral-900">
          {displayName}
        </h3>

        {/* Price display: trial "FREE" treatment vs standard cents */}
        {isTrialTier ? (
          <div className="flex flex-col">
            <span
              className="text-2xl font-bold text-brand-600"
              data-testid={`${testID ?? `tier-picker-card-${tierName}`}-price-free`}
            >
              FREE
            </span>
            {trialDurationDays !== undefined && (
              <span className="text-sm text-neutral-500">
                for {trialDurationDays} days
              </span>
            )}
          </div>
        ) : (
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-neutral-900">
              {formatCents(monthlyPriceCents)}
            </span>
            <span className="text-sm text-neutral-500">/mo</span>
          </div>
        )}

        {annualPriceCents && !isTrialTier && (
          <p className="text-xs text-margin-600">
            {formatCents(annualPriceCents)}/yr — save{" "}
            {Math.round(
              ((monthlyPriceCents * 12 - annualPriceCents) /
                (monthlyPriceCents * 12)) *
                100,
            )}
            %
          </p>
        )}
      </div>

      {/* Feature list */}
      <ul
        className="flex flex-col gap-2"
        aria-label={`${displayName} features`}
      >
        {/* Synthetic maxUsers row (rendered before explicit features) */}
        {maxUsers !== undefined && (
          <li className="flex items-center gap-2 text-sm text-neutral-700">
            <svg
              className="w-4 h-4 flex-shrink-0 text-margin-600"
              fill="none"
              viewBox="0 0 16 16"
              aria-label="Included"
            >
              <path
                d="M3 8l3.5 3.5 6.5-7"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>Up to {maxUsers} users</span>
          </li>
        )}

        {features.map((feature) => (
          <li
            key={feature.label}
            className={`flex items-center gap-2 text-sm ${
              feature.included ? "text-neutral-700" : "text-neutral-400"
            }`}
          >
            {feature.included ? (
              <svg
                className="w-4 h-4 flex-shrink-0 text-margin-600"
                fill="none"
                viewBox="0 0 16 16"
                aria-label="Included"
              >
                <path
                  d="M3 8l3.5 3.5 6.5-7"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <svg
                className="w-4 h-4 flex-shrink-0 text-neutral-300"
                fill="none"
                viewBox="0 0 16 16"
                aria-label="Not included"
              >
                <path
                  d="M4 4l8 8M12 4l-8 8"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            )}
            <span className={feature.included ? "" : "line-through"}>
              {feature.label}
            </span>
            {feature.callout && (
              <span className="ml-auto text-xs text-neutral-500 font-medium">
                {feature.callout}
              </span>
            )}
          </li>
        ))}
      </ul>

      {/* CTA — or "(current)" when isCurrentTier */}
      {isCurrentTier ? (
        <div
          className="mt-auto w-full py-2 px-4 rounded-lg text-sm font-semibold text-center text-neutral-500 bg-neutral-100"
          data-testid={`${testID ?? `tier-picker-card-${tierName}`}-current-label`}
        >
          (current)
        </div>
      ) : (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(tierName);
          }}
          aria-label={resolvedCtaLabel}
          className={`
            mt-auto w-full py-2 px-4 rounded-lg text-sm font-semibold
            transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
            ${
              isSelected || isFeatured
                ? "bg-brand-600 text-white hover:bg-brand-800"
                : "bg-neutral-100 text-neutral-800 hover:bg-neutral-200"
            }
          `}
        >
          {isSelected ? "Selected" : resolvedCtaLabel}
        </button>
      )}
    </div>
  );
}
