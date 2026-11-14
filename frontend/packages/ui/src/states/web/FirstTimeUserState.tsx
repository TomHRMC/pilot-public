/**
 * FirstTimeUserState — Web variant
 *
 * Location: packages/ui/src/states/web/FirstTimeUserState.tsx
 * Rendered by: Tailwind CSS utility classes (no hardcoded design values)
 *
 * 8-variant FTU state for new tenants seeing a surface for the first time.
 * All 8 variants are supported on web.
 */

import React from "react";
import type { FirstTimeUserStateProps } from "../types";
import { FTU_DEFAULTS } from "../types";

/**
 * FirstTimeUserState (web)
 *
 * @example
 * <FirstTimeUserState type="quotes" />
 * <FirstTimeUserState type="dashboard" onCta={() => router.push('/settings/team')} />
 */
export function FirstTimeUserState({
  type,
  headingText,
  bodyText,
  ctaLabel,
  onCta,
  secondaryCtaLabel,
  onSecondaryCta,
  testID,
}: FirstTimeUserStateProps) {
  const defaults = FTU_DEFAULTS[type];
  const resolvedHeading = headingText ?? defaults.heading;
  const resolvedBody = bodyText ?? defaults.body;
  const resolvedCtaLabel = ctaLabel ?? defaults.ctaLabel;

  return (
    <section
      role="region"
      aria-label={`First time setup: ${resolvedHeading}`}
      data-testid={testID ?? `ftu-state-${type}`}
      className="flex flex-col items-center justify-center gap-6 px-8 py-16 text-center"
    >
      {/* Pilot logo mark / onboarding illustration placeholder */}
      <div
        className="w-16 h-16 rounded-full bg-brand-100 flex items-center justify-center"
        aria-hidden="true"
      >
        <svg
          className="w-8 h-8 text-brand-600"
          fill="none"
          viewBox="0 0 32 32"
          aria-hidden="true"
        >
          <path
            d="M16 4L28 28H4L16 4Z"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
            strokeLinejoin="round"
          />
          <line
            x1="16"
            y1="14"
            x2="16"
            y2="20"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="16" cy="24" r="1" fill="currentColor" />
        </svg>
      </div>

      <div className="flex flex-col gap-3 max-w-md">
        <h2 className="text-h2 font-semibold text-neutral-900">
          {resolvedHeading}
        </h2>
        <p className="text-body text-neutral-500">{resolvedBody}</p>
      </div>

      <div className="flex flex-col items-center gap-3">
        <button
          type="button"
          onClick={onCta}
          aria-label={resolvedCtaLabel}
          className="px-6 py-3 rounded-lg bg-brand-600 text-white text-sm font-semibold hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 transition-colors"
        >
          {resolvedCtaLabel}
        </button>

        {secondaryCtaLabel && (
          <button
            type="button"
            onClick={onSecondaryCta}
            aria-label={secondaryCtaLabel}
            className="text-sm text-neutral-500 underline hover:text-neutral-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 focus-visible:ring-offset-2"
          >
            {secondaryCtaLabel}
          </button>
        )}
      </div>
    </section>
  );
}
