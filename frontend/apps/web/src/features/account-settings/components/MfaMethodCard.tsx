/**
 * MfaMethodCard — MFA-WIRE-1 Part B (spec §2.3, §2.4)
 *
 * Location: apps/web/src/features/account-settings/components/MfaMethodCard.tsx
 *
 * Surface-scoped single method card. Renders one enrolled MFA method with:
 *   - Leading icon (ShieldCheckIcon TOTP / DevicePhoneMobileIcon SMS)
 *   - Label ("Authenticator app" / "Text message")
 *   - Secondary line (destination_masked · Enrolled {date} for SMS; Enrolled {date} for TOTP)
 *   - Remove text-button (destructive)
 *   - Pending state: opacity-60 + pointer-events-none + <PendingBadge> + aria-busy
 *
 * `last_used_at` is NEVER rendered (spec §2.3 — always null this batch).
 *
 * NOT exported from packages/ui — surface-scoped by design (§I).
 */
"use client";

import React from "react";
import {
  ShieldCheckIcon,
  DevicePhoneMobileIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { PendingBadge } from "@pilot/ui";
import type { components } from "@pilot/shared-types";

type MfaMethodInfo = components["schemas"]["MfaMethodInfo"];

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const METHOD_LABELS: Record<string, string> = {
  totp: "Authenticator app",
  sms: "Text message",
};

export interface MfaMethodCardProps {
  method: MfaMethodInfo;
  isPending: boolean;
  onRemove: () => void;
}

export function MfaMethodCard({
  method,
  isPending,
  onRemove,
}: MfaMethodCardProps) {
  const methodType = method.method_type;
  const label = METHOD_LABELS[methodType] ?? methodType;
  const isTotp = methodType === "totp";
  const isSms = methodType === "sms";

  const Icon = isTotp ? ShieldCheckIcon : DevicePhoneMobileIcon;

  const enrolledDate = dateFormatter.format(new Date(method.enrolled_at));
  const secondaryLine = isSms
    ? `${method.destination_masked ?? ""} · Enrolled ${enrolledDate}`
    : `Enrolled ${enrolledDate}`;

  const cardTestId = `mfa-method-card-${methodType}`;
  const removeTestId = `mfa-method-remove-${methodType}`;

  return (
    <div
      data-testid={isPending ? `${cardTestId}-pending` : cardTestId}
      aria-busy={isPending}
      className={`rounded-lg border border-neutral-200 bg-white px-4 py-3 flex items-center gap-3 min-h-[64px] transition-opacity duration-150 ease-in-out motion-reduce:transition-none ${
        isPending ? "opacity-60 pointer-events-none" : ""
      }`}
    >
      {/* Leading icon */}
      <div
        className="flex-shrink-0 w-10 h-10 rounded-full bg-brand-50 flex items-center justify-center"
        aria-hidden="true"
      >
        <Icon className="w-5 h-5 text-brand-600" />
      </div>

      {/* Label + secondary line */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-neutral-900">{label}</span>
          {isPending && (
            <PendingBadge
              count={1}
              variant="pending"
              accessibilityLabel="Removing method"
              className="ml-2"
            />
          )}
        </div>
        <p className="text-xs text-neutral-500 mt-0.5 truncate">
          {secondaryLine}
        </p>
      </div>

      {/* Remove action — hidden when pending (replaced by badge) */}
      {!isPending && (
        <button
          type="button"
          onClick={onRemove}
          data-testid={removeTestId}
          aria-label={`Remove ${label} method`}
          className="flex items-center gap-1.5 text-sm font-medium text-fault-600 hover:text-fault-700 active:text-fault-800 px-2 py-2 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2 transition-colors duration-150 ease-in-out motion-reduce:transition-none"
        >
          <TrashIcon className="w-4 h-4" aria-hidden="true" />
          Remove
        </button>
      )}
    </div>
  );
}
