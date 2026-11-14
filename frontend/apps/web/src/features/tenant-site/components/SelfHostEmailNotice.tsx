"use client";

/**
 * SelfHostEmailNotice — C-B16 "Guide emailed on {date}" state display
 *
 * Location: apps/web/src/features/tenant-site/components/SelfHostEmailNotice.tsx
 *
 * Shows when the one-time requirements email has been sent (§G-19).
 * This is a STATE DISPLAY, not a resend button — the email is one-time by design.
 * No resend affordance anywhere (Design Decision #9).
 *
 * web spec §12.5: bg-margin-50, EnvelopeIcon, formatted date.
 */

import React from "react";
import { EnvelopeIcon } from "@heroicons/react/24/solid";

interface SelfHostEmailNoticeProps {
  /** ISO date string of when the requirements email was sent */
  requirementsEmailedAt: string;
}

function formatDate(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return isoDate;
  }
}

export function SelfHostEmailNotice({
  requirementsEmailedAt,
}: SelfHostEmailNoticeProps) {
  return (
    <div className="mt-3 flex items-start gap-2 rounded-md border border-margin-200 bg-margin-50 p-3">
      <EnvelopeIcon
        className="h-4 w-4 shrink-0 text-margin-600"
        aria-hidden="true"
      />
      <div>
        <p className="text-sm font-medium text-margin-700">
          Requirements guide emailed on {formatDate(requirementsEmailedAt)}
        </p>
        <p className="mt-0.5 text-xs text-margin-600">
          (The guide is always downloadable above — no need to resend.)
        </p>
      </div>
    </div>
  );
}
