/**
 * ErrorState — Web variant
 *
 * Location: packages/ui/src/states/web/ErrorState.tsx
 * Rendered by: Tailwind CSS utility classes (no hardcoded design values)
 *
 * Four variants: network | server | validation | permission
 * Uses role="alert" and aria-live="assertive" for screen reader accessibility.
 */

import React from "react";
import type { ErrorStateProps } from "../types";
import { ERROR_STATE_DEFAULTS } from "../types";

/**
 * ErrorState (web)
 *
 * @example
 * <ErrorState type="network" onRetry={() => refetch()} />
 * <ErrorState type="validation" fieldErrors={{ email: "Invalid email address" }} />
 */
export function ErrorState({
  type,
  title,
  description,
  onRetry,
  fieldErrors,
  onContactSupport,
  testID,
}: ErrorStateProps) {
  const defaults = ERROR_STATE_DEFAULTS[type];
  const resolvedTitle = title ?? defaults.title;
  const resolvedDescription = description ?? defaults.description;

  const showRetryCta = (type === "network" || type === "server") && onRetry;
  const showContactSupport = type === "server" && onContactSupport;
  const showFieldErrors =
    type === "validation" && fieldErrors && Object.keys(fieldErrors).length > 0;

  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid={testID ?? `error-state-${type}`}
      className="flex flex-col gap-4 rounded-lg border border-fault-200 bg-fault-50 p-6"
    >
      <div className="flex items-start gap-3">
        {/* Error icon */}
        <svg
          className="w-5 h-5 flex-shrink-0 mt-0.5 text-fault-600"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="2"
          />
          <line
            x1="12"
            y1="8"
            x2="12"
            y2="12"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="12" cy="16" r="1" fill="currentColor" />
        </svg>

        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold text-fault-800">
            {resolvedTitle}
          </h2>
          <p className="text-sm text-fault-700">{resolvedDescription}</p>
        </div>
      </div>

      {/* Inline field errors for validation type */}
      {showFieldErrors && (
        <ul className="flex flex-col gap-1 pl-8" aria-label="Field errors">
          {Object.entries(fieldErrors!).map(([field, error]) => (
            <li key={field} className="text-sm text-fault-700">
              <span className="font-medium capitalize">{field}:</span> {error}
            </li>
          ))}
        </ul>
      )}

      {/* CTAs */}
      {(showRetryCta || showContactSupport) && (
        <div className="flex items-center gap-3 pl-8">
          {showRetryCta && (
            <button
              type="button"
              onClick={onRetry}
              className="text-sm font-medium text-fault-700 underline hover:text-fault-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-fault-600 focus-visible:ring-offset-2"
              aria-label="Retry"
            >
              Try again
            </button>
          )}
          {showContactSupport && (
            <button
              type="button"
              onClick={onContactSupport}
              className="text-sm font-medium text-neutral-600 underline hover:text-neutral-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 focus-visible:ring-offset-2"
              aria-label="Contact support"
            >
              Contact support
            </button>
          )}
        </div>
      )}
    </div>
  );
}
