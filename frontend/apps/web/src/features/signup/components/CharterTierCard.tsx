/**
 * CharterTierCard — Step 4 Charter tier selection card
 *
 * Location: apps/web/src/features/signup/components/CharterTierCard.tsx
 *
 * C-B5: Purpose-built card for the Charter tier. Composes the visual language
 * of TierPickerCard (rounded-xl, border-2, p-6, feature list with checkmark
 * icons) but is a distinct component because:
 *  - The price display is a fixed "$49/month" with a "Free for 90 days" callout
 *  - The free-period copy is plain-language and derived from free_period_days
 *  - The charter_member_number is NOT shown here (assigned server-side)
 *
 * TierPickerCard interface is FROZEN after FE-B13 — this feature-specific
 * component is the correct placement (§6: domain-specific → features/[domain]/components/).
 */

"use client";

import React from "react";
import { GiftIcon, CheckCircleIcon } from "@heroicons/react/24/outline";
import type { SubscriptionTierAPI } from "../types";

interface CharterTierCardProps {
  tier: SubscriptionTierAPI;
  isSelected: boolean;
  onSelect: () => void;
}

export function CharterTierCard({
  tier,
  isSelected,
  onSelect,
}: CharterTierCardProps): React.ReactElement {
  const freePeriodDays = tier.free_period_days ?? 90;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect();
    }
  };

  return (
    <div
      data-testid="charter-tier-card"
      role="radio"
      aria-checked={isSelected}
      aria-label={`Charter tier, ${freePeriodDays} days free, no card needed`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onClick={onSelect}
      className={`
        relative flex flex-col gap-4 rounded-xl border-2 p-6
        transition-all cursor-pointer
        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
        ${
          isSelected
            ? "border-brand-600 bg-brand-50 shadow-md"
            : "border-brand-200 bg-white shadow-sm hover:border-brand-300 hover:shadow-md"
        }
      `}
    >
      {/* Featured badge */}
      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
        <span className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold bg-brand-600 text-white">
          Charter Program
        </span>
      </div>

      {/* Selected checkmark (corner) */}
      {isSelected && (
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

      {/* Tier name */}
      <h3 className="text-h3 font-semibold text-neutral-900">
        {tier.display_label}
      </h3>

      {/* Price */}
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold text-neutral-900">$49</span>
        <span className="text-sm text-neutral-500">/mo</span>
      </div>

      {/* Free-period callout */}
      <div
        className="bg-margin-50 border border-margin-200 rounded-md px-3 py-2 flex items-center gap-2"
        data-testid="charter-free-period-callout"
      >
        <GiftIcon className="w-4 h-4 text-margin-600 flex-shrink-0" />
        <span className="text-sm text-margin-700 font-medium">
          Free for {freePeriodDays} days. No card needed.
        </span>
      </div>

      {/* Feature list */}
      <ul className="flex flex-col gap-2" aria-label="Charter tier features">
        <li className="flex items-center gap-2 text-sm text-neutral-700">
          <CheckCircleIcon className="w-4 h-4 text-margin-600 flex-shrink-0" />
          <span>Voice quoting</span>
        </li>
        <li className="flex items-center gap-2 text-sm text-neutral-700">
          <CheckCircleIcon className="w-4 h-4 text-margin-600 flex-shrink-0" />
          <span>Job management</span>
        </li>
        <li className="flex items-center gap-2 text-sm text-neutral-700">
          <CheckCircleIcon className="w-4 h-4 text-margin-600 flex-shrink-0" />
          <span>QuickBooks sync</span>
        </li>
        <li className="flex items-center gap-2 text-sm text-neutral-700">
          <CheckCircleIcon className="w-4 h-4 text-margin-600 flex-shrink-0" />
          <span>SMS notifications</span>
        </li>
        <li className="flex items-center gap-2 text-sm text-neutral-700">
          <CheckCircleIcon className="w-4 h-4 text-margin-600 flex-shrink-0" />
          <span>Team members</span>
          <span className="ml-auto text-xs text-neutral-500 font-medium">
            Up to {tier.max_users}
          </span>
        </li>
      </ul>

      {/* CTA button */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        aria-label={isSelected ? "Selected" : "Select Charter"}
        className={`
          mt-auto w-full py-2 px-4 rounded-lg text-sm font-semibold
          transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
          ${
            isSelected
              ? "bg-brand-600 text-white"
              : "bg-brand-600 text-white hover:bg-brand-800"
          }
        `}
        data-testid="charter-tier-select-button"
      >
        {isSelected ? "Selected" : "Select Charter"}
      </button>
    </div>
  );
}
