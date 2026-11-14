/**
 * SmsOptOutBadge — Customer opt-out indicator chip
 *
 * Location: packages/ui/src/sms-opt-out-badge/SmsOptOutBadge.tsx
 * Platform: Web (React DOM) — mobile uses same TSX via Metro resolver
 * Exported from: packages/ui/src/index.ts under // ── FE-B10 Exports ──
 *
 * Token classes:
 *   Web:   bg-fault-50 border border-fault-200 text-fault-800
 *   Mobile: uses fault color tokens from tokens.ts
 *
 * Design doc Section A.1.4: compact chip shown in thread headers
 * when customer.sms_opted_out === true.
 */

import React from "react";
import type { SmsOptOutBadgeProps } from "./types";

function formatOptOutDate(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function SmsOptOutBadge({
  optedOutAt,
  compact = false,
  testID,
}: SmsOptOutBadgeProps) {
  const label =
    optedOutAt && !compact
      ? `SMS opted out · ${formatOptOutDate(optedOutAt)}`
      : "SMS opted out";

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-caption font-medium bg-fault-50 border border-fault-200 text-fault-800"
      data-testid={testID ?? "sms-opt-out-badge"}
      aria-label={label}
    >
      {label}
    </span>
  );
}
