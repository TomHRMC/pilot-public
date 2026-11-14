/**
 * ConflictSeverityBadge — Color-coded badge for dispatch conflict classes
 *
 * Location: apps/web/src/features/dispatch-board/components/ConflictSeverityBadge.tsx
 *
 * Encodes overlap / availability / travel / info conflict class per §13.4.
 * Uses CONFLICT_CLASS_TOKENS from packages/ui — no local token re-definition.
 *
 * Per batch-fe-b4-design.md §A.2.3
 * Shared pattern consumed by FE-B7, FE-B8, FE-B9 — do not change token mapping.
 */

import React from "react";
import { CONFLICT_CLASS_TOKENS } from "@pilot/ui";
import type { DispatchConflictClass } from "@pilot/ui";

interface ConflictSeverityBadgeProps {
  conflictClass: DispatchConflictClass;
}

/**
 * ConflictSeverityBadge
 *
 * Renders a small colored badge labeling the conflict class.
 * Token colors from CONFLICT_CLASS_TOKENS (packages/ui/src/conflict-severity).
 */
export function ConflictSeverityBadge({
  conflictClass,
}: ConflictSeverityBadgeProps) {
  const tokens = CONFLICT_CLASS_TOKENS[conflictClass];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-caption font-medium ${tokens.badgeBgClass} ${tokens.badgeTextClass}`}
      aria-label={`Conflict type: ${tokens.badgeText}`}
    >
      {/* Icon */}
      <ConflictIcon iconName={tokens.iconName} />
      {tokens.badgeText}
    </span>
  );
}

function ConflictIcon({ iconName }: { iconName: string }) {
  switch (iconName) {
    case "alert-circle":
      return (
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5 0a5 5 0 100 10A5 5 0 005 0zm0 2.5a.5.5 0 01.5.5v2a.5.5 0 01-1 0V3a.5.5 0 01.5-.5zm0 5a.667.667 0 100-1.333.667.667 0 000 1.333z"
            clipRule="evenodd"
          />
        </svg>
      );
    case "clock":
      return (
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5 0a5 5 0 100 10A5 5 0 005 0zM4.5 2.5a.5.5 0 011 0v2.793l1.354 1.353a.5.5 0 11-.708.708l-1.5-1.5A.5.5 0 014.5 5.5V2.5z"
            clipRule="evenodd"
          />
        </svg>
      );
    case "map-pin":
      return (
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5 0C3.067 0 1.5 1.567 1.5 3.5c0 2.625 3.5 6.5 3.5 6.5S8.5 6.125 8.5 3.5C8.5 1.567 6.933 0 5 0zm0 4.5a1 1 0 100-2 1 1 0 000 2z"
            clipRule="evenodd"
          />
        </svg>
      );
    case "info":
    default:
      return (
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5 0a5 5 0 100 10A5 5 0 005 0zm0 2a.75.75 0 110 1.5A.75.75 0 015 2zm-.5 2.5h1v3h-1v-3z"
            clipRule="evenodd"
          />
        </svg>
      );
  }
}
