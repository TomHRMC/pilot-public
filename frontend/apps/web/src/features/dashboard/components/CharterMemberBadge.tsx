/**
 * CharterMemberBadge — Owner-only dashboard badge showing charter member number + free-until date
 *
 * Location: apps/web/src/features/dashboard/components/CharterMemberBadge.tsx
 *
 * C-B5: A non-interactive display-only badge shown on the dashboard header.
 * Communicates two things:
 *  1. The tenant is a Charter Member, with their number: "Charter Member #N"
 *  2. The current free_period_ends_at as a date: "Free until Aug 14, 2026"
 *
 * Owner-only RBAC: wrapped in <RoleGate role="owner"> by the dashboard page.
 * Returns null when charterMemberNumber is null/undefined.
 * Omits "Free until" portion when freePeriodEndsAt is null.
 */

"use client";

import React from "react";
import { StarIcon } from "@heroicons/react/24/solid";

interface CharterMemberBadgeProps {
  charterMemberNumber: number;
  freePeriodEndsAt: string | null;
}

export function CharterMemberBadge({
  charterMemberNumber,
  freePeriodEndsAt,
}: CharterMemberBadgeProps): React.ReactElement | null {
  if (charterMemberNumber == null) return null;

  const formattedDate = freePeriodEndsAt
    ? new Date(freePeriodEndsAt).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  const ariaLabel = freePeriodEndsAt
    ? `Charter Member number ${charterMemberNumber}, free until ${formattedDate}`
    : `Charter Member number ${charterMemberNumber}`;

  return (
    <div
      className="inline-flex items-center gap-2 rounded-full px-3 py-1 bg-brand-50 border border-brand-200"
      aria-label={ariaLabel}
      data-testid="charter-member-badge"
    >
      <StarIcon className="w-4 h-4 text-brand-600" aria-hidden="true" />
      <span className="text-sm font-semibold text-brand-700">
        Charter Member #{charterMemberNumber}
      </span>
      {formattedDate && (
        <>
          <span className="text-brand-300" aria-hidden="true">
            ·
          </span>
          <span className="text-xs text-brand-600">
            Free until {formattedDate}
          </span>
        </>
      )}
    </div>
  );
}
