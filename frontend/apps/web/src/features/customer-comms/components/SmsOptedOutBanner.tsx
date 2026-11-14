/**
 * SmsOptedOutBanner — Fault-color banner shown when customer has opted out
 *
 * Location: apps/web/src/features/customer-comms/components/SmsOptedOutBanner.tsx
 *
 * Contains SmsOptOutBadge. Appears at top of thread view.
 *
 * Token classes:
 *   bg-fault-50 border-fault-200 text-fault-800
 *
 * Design doc Section A.2.1, Decision 7
 */

"use client";

import React from "react";
import { SmsOptOutBadge } from "@pilot/ui";

interface SmsOptedOutBannerProps {
  optedOutAt: string | null;
  testID?: string;
}

export function SmsOptedOutBanner({
  optedOutAt,
  testID,
}: SmsOptedOutBannerProps) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3 bg-fault-50 border border-fault-200 rounded-lg mb-4"
      data-testid={testID ?? "sms-opted-out-banner"}
      role="alert"
    >
      <SmsOptOutBadge optedOutAt={optedOutAt} testID="opted-out-badge" />
      <p className="text-body text-fault-800">
        This customer has opted out of SMS — they cannot be reached via text.
        Historical messages are preserved for your records.
      </p>
    </div>
  );
}
