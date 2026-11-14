/**
 * LoadingState — Web variant
 *
 * Location: packages/ui/src/states/web/LoadingState.tsx
 * Rendered by: Tailwind CSS utility classes (no hardcoded design values)
 *
 * Three variants:
 *   - full-page: skeleton rows placeholder for initial page loads
 *   - inline: spinning indicator for embedded async areas
 *   - optimistic: pulse animation wrapping children with pending operation
 */

import React from "react";
import type { LoadingStateProps } from "../types";

/**
 * SkeletonRow — a single animated placeholder row
 */
function SkeletonRow({ index }: { index: number }) {
  // Vary widths to simulate real content shapes
  const widths = ["w-full", "w-4/5", "w-3/4", "w-2/3", "w-5/6", "w-full"];
  const width = widths[index % widths.length] ?? "w-full";

  return (
    <div
      className={`h-4 rounded-md bg-neutral-200 animate-pulse ${width}`}
      aria-hidden="true"
    />
  );
}

/**
 * LoadingState (web)
 *
 * @example
 * <LoadingState type="full-page" skeletonRows={6} />
 * <LoadingState type="inline" label="Saving quote…" />
 * <LoadingState type="optimistic"><QuoteCard /></LoadingState>
 */
export function LoadingState({
  type,
  skeletonRows = 4,
  label = "Loading\u2026",
  children,
  testID,
}: LoadingStateProps) {
  if (type === "full-page") {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label={label}
        data-testid={testID ?? "loading-state-full-page"}
        className="flex flex-col gap-4 p-8 w-full"
      >
        {Array.from({ length: skeletonRows }, (_, i) => (
          <SkeletonRow key={i} index={i} />
        ))}
        <span className="sr-only">{label}</span>
      </div>
    );
  }

  if (type === "inline") {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label={label}
        data-testid={testID ?? "loading-state-inline"}
        className="inline-flex items-center gap-2"
      >
        {/* Spinner ring */}
        <svg
          className="w-4 h-4 animate-spin text-brand-600"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span className="text-sm text-neutral-500">{label}</span>
        <span className="sr-only">{label}</span>
      </div>
    );
  }

  // optimistic — wraps children with a subtle pulse
  return (
    <div
      data-testid={testID ?? "loading-state-optimistic"}
      className="animate-pulse opacity-70"
      aria-busy="true"
    >
      {children}
    </div>
  );
}
