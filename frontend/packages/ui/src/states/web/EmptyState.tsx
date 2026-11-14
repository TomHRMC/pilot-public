/**
 * EmptyState — Web variant
 *
 * Location: packages/ui/src/states/web/EmptyState.tsx
 * Rendered by: shadcn/ui primitives + Tailwind utility classes
 *
 * All colors resolve via Tailwind token classes from pilotPreset.
 * No hardcoded hex values — all design values come from tokens.
 */

import React from "react";
import type { EmptyStateProps } from "../types";
import { EMPTY_STATE_DEFAULTS } from "../types";

/** Illustration mapping — returns an accessible SVG per illustration key */
function IllustrationIcon({
  type,
}: {
  type: NonNullable<EmptyStateProps["illustration"]>;
}) {
  if (type === "none") return null;

  const baseClass = "w-12 h-12 text-neutral-400";

  switch (type) {
    case "empty-clipboard":
      return (
        <svg
          className={baseClass}
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <rect
            x="10"
            y="8"
            width="28"
            height="36"
            rx="4"
            className="stroke-neutral-300"
            strokeWidth="2"
            fill="none"
          />
          <rect
            x="18"
            y="4"
            width="12"
            height="8"
            rx="2"
            className="stroke-neutral-300"
            strokeWidth="2"
            fill="none"
          />
          <line
            x1="16"
            y1="22"
            x2="32"
            y2="22"
            className="stroke-neutral-200"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <line
            x1="16"
            y1="30"
            x2="28"
            y2="30"
            className="stroke-neutral-200"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      );
    case "lock":
      return (
        <svg
          className={baseClass}
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <rect
            x="10"
            y="22"
            width="28"
            height="20"
            rx="4"
            className="stroke-neutral-300"
            strokeWidth="2"
            fill="none"
          />
          <path
            d="M16 22v-6a8 8 0 0116 0v6"
            className="stroke-neutral-300"
            strokeWidth="2"
            fill="none"
          />
          <circle cx="24" cy="32" r="3" className="fill-neutral-300" />
        </svg>
      );
    case "wrench":
      return (
        <svg
          className={baseClass}
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M32 8a10 10 0 00-10 10c0 1.3.25 2.54.7 3.67L8 36a4 4 0 005.66 5.66L28.33 27.3A10 10 0 1032 8z"
            className="stroke-neutral-300"
            strokeWidth="2"
            fill="none"
          />
        </svg>
      );
    case "filter":
      return (
        <svg
          className={baseClass}
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M8 14h32M16 24h16M22 34h4"
            className="stroke-neutral-300"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      );
    default:
      return null;
  }
}

/**
 * EmptyState (web)
 *
 * Renders a centered region indicating an empty/unavailable data set.
 * Discriminated by `type` prop — all 5 variants use a single component.
 *
 * @example
 * <EmptyState type="no-data" ctaLabel="Create your first quote" onCta={handleCreate} />
 */
export function EmptyState({
  type,
  title,
  description,
  ctaLabel,
  onCta,
  secondaryCtaLabel,
  onSecondaryCta,
  illustration,
  testID,
}: EmptyStateProps) {
  const defaults = EMPTY_STATE_DEFAULTS[type];
  const resolvedTitle = title ?? defaults.title;
  const resolvedDescription = description ?? defaults.description;
  const resolvedIllustration = illustration ?? defaults.illustration;

  return (
    <section
      role="region"
      aria-label={resolvedTitle}
      data-testid={testID ?? `empty-state-${type}`}
      className="flex flex-col items-center justify-center gap-4 px-8 py-12 text-center"
    >
      <IllustrationIcon type={resolvedIllustration} />

      <div className="flex flex-col gap-2">
        <h2 className="text-h3 font-semibold text-neutral-800">
          {resolvedTitle}
        </h2>
        <p className="text-body text-neutral-500 max-w-sm">
          {resolvedDescription}
        </p>
      </div>

      {(onCta ?? ctaLabel) && (
        <div className="flex flex-col items-center gap-2 mt-2">
          <button
            type="button"
            onClick={onCta}
            className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 transition-colors"
            aria-label={ctaLabel}
          >
            {ctaLabel}
          </button>

          {secondaryCtaLabel && (
            <button
              type="button"
              onClick={onSecondaryCta}
              className="text-sm text-brand-600 hover:text-brand-800 underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
              aria-label={secondaryCtaLabel}
            >
              {secondaryCtaLabel}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
