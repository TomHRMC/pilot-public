/**
 * TrialExpiryBanner — Soft-gate dismissable banner in (authed) layout header
 *
 * Location: apps/web/src/features/onboarding/components/TrialExpiryBanner.tsx
 *
 * Token audit (Section H):
 *  - 7d / 3d: text-alert-600 bg-alert-50 (amber warning)
 *  - 1d / 0d expired: text-fault-600 bg-fault-50 (red urgent)
 *
 * 7d/3d/1d: dismissable banner; re-appears on next session.
 * 0d: hard gate renders TrialExpiredPage instead of content (see (authed)/layout).
 */

"use client";

import React, { useState } from "react";

interface TrialExpiryBannerProps {
  daysRemaining: number;
  onUpgradeClick: () => void;
}

export function TrialExpiryBanner({
  daysRemaining,
  onUpgradeClick,
}: TrialExpiryBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || daysRemaining > 7) return null;

  const isUrgent = daysRemaining <= 1;

  const bannerText =
    daysRemaining === 0
      ? "Your trial has expired."
      : daysRemaining === 1
        ? "Your trial ends today!"
        : `Your trial ends in ${daysRemaining} day${daysRemaining === 1 ? "" : "s"}.`;

  return (
    <div
      role="alert"
      aria-live="polite"
      data-testid="trial-expiry-banner"
      className={`
        flex items-center justify-between px-4 py-2 text-sm
        ${
          isUrgent ? "bg-fault-50 text-fault-600" : "bg-alert-50 text-alert-600"
        }
      `}
    >
      <span>
        {bannerText}{" "}
        <button
          type="button"
          onClick={onUpgradeClick}
          data-testid="trial-banner-upgrade-button"
          className={`
            font-semibold underline focus:outline-none focus-visible:ring-2
            focus-visible:ring-offset-1 rounded
            ${
              isUrgent
                ? "focus-visible:ring-fault-600"
                : "focus-visible:ring-alert-600"
            }
          `}
        >
          Upgrade now
        </button>
      </span>

      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss trial expiry banner"
        data-testid="trial-banner-dismiss"
        className={`
          ml-4 text-sm opacity-60 hover:opacity-100 focus:outline-none
          focus-visible:ring-2 focus-visible:ring-offset-1 rounded
          ${isUrgent ? "focus-visible:ring-fault-600" : "focus-visible:ring-alert-600"}
        `}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 16 16"
          aria-hidden="true"
        >
          <path
            d="M3 3l10 10M13 3L3 13"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  );
}
