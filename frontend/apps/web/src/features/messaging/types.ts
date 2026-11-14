/**
 * Messaging feature — shared types
 *
 * Location: apps/web/src/features/messaging/types.ts
 *
 * C-B9: 10DLC provisioning state machine types. These mirror the backend
 * ProvisioningStatusResponse.status values (design doc §F.1 MESSAGING_STATES).
 *
 * RULE 1.3: API payload types come from @pilot/shared-types. These local types
 * are for UI state-machine logic (status → panel mapping) and are NOT a
 * substitute for the generated API types.
 */

/** All provisioning status values from the backend state machine. */
export type MessagingStatus =
  | "not_started"
  | "quoting"
  | "awaiting_payment"
  | "payment_failed"
  | "brand_submitted"
  | "awaiting_otp"
  | "brand_verified"
  | "brand_rejected"
  | "campaign_submitted"
  | "awaiting_number_selection"
  | "campaign_rejected"
  | "number_assigned"
  | "active"
  | "suspended";

/** Entity type determines the provisioning path (standard vs sole-prop OTP). */
export type EntityType = "standard" | "sole_proprietor";

/** Provisioning step labels for the status indicator. */
export type ProvisioningStep =
  | "brand"
  | "payment"
  | "verify"
  | "campaign"
  | "number"
  | "activate"
  | "active";

/** Step state for the status indicator. */
export type StepState = "done" | "in-progress" | "pending" | "error";

/** Statuses that should trigger polling (5s refetchInterval). */
export const POLLING_STATUSES: ReadonlySet<MessagingStatus> = new Set([
  "brand_submitted",
  "awaiting_otp",
  "brand_verified",
  "campaign_submitted",
  "awaiting_number_selection",
  "number_assigned",
  "awaiting_payment",
]);

/** Terminal statuses — stop polling. */
export const TERMINAL_STATUSES: ReadonlySet<MessagingStatus> = new Set([
  "active",
  "brand_rejected",
  "campaign_rejected",
  "suspended",
  "payment_failed",
  "quoting",
]);

/** Error panel variants. */
export type ErrorPanelVariant = "payment_failed" | "rejected" | "suspended";

/**
 * Maps a MessagingStatus to the error panel variant, or null if not an error.
 */
export function getErrorVariant(
  status: MessagingStatus,
): ErrorPanelVariant | null {
  if (status === "payment_failed") return "payment_failed";
  if (status === "brand_rejected" || status === "campaign_rejected")
    return "rejected";
  if (status === "suspended") return "suspended";
  return null;
}

/**
 * Millicents → USD display. 1 millicent = $0.00001.
 * @example formatMillicentsAsUSD(400000) → "$4.00"
 */
export function formatMillicentsAsUSD(millicents: number): string {
  return `$${(millicents / 100000).toFixed(2)}`;
}

/**
 * Millicents → per-segment USD display (3 decimal places for sub-cent rates).
 * @example formatMillicentsPerSegment(300) → "$0.003/segment"
 */
export function formatMillicentsPerSegment(millicents: number): string {
  return `$${(millicents / 100000).toFixed(3)}/segment`;
}

/**
 * Format a phone number for display: "+13025551234" → "(302) 555-1234".
 * Returns the original string if it doesn't match the expected format.
 */
export function formatPhoneNumber(phone: string | null): string {
  if (!phone) return "";
  // Strip non-digits
  const digits = phone.replace(/\D/g, "");
  // US format: 1 + 10 digits
  if (digits.length === 11 && digits.startsWith("1")) {
    const area = digits.slice(1, 4);
    const prefix = digits.slice(4, 7);
    const line = digits.slice(7, 11);
    return `(${area}) ${prefix}-${line}`;
  }
  // 10 digits without country code
  if (digits.length === 10) {
    const area = digits.slice(0, 3);
    const prefix = digits.slice(3, 6);
    const line = digits.slice(6, 10);
    return `(${area}) ${prefix}-${line}`;
  }
  return phone;
}
