/**
 * SMS Quota State Utilities
 *
 * Location: packages/ui/src/sms-quota-indicator/utils.ts
 * Exported from: packages/ui/src/index.ts under // ── FE-B10 Exports ──
 */

import type { SmsQuotaStatus } from "../sms-thread-bubble/types";
import type { QuotaVisualState } from "../sms-thread-bubble/types";

/**
 * deriveQuotaState — maps raw SmsQuotaStatus to a discriminated QuotaVisualState.
 *
 * Priority order:
 *  1. opted_out — when blocked_reason === 'customer_opted_out'
 *  2. blocked_hard — when monthly_quota_reached AND cap_policy === 'hard'
 *  3. blocked_soft — when remaining === 0 AND cap_policy === 'soft'
 *  4. warning — when remaining > 0 AND remaining / included ≤ 0.2
 *  5. normal — all other states
 *
 * This function is a pure utility — safe to use outside React components.
 */
export function deriveQuotaState(quota: SmsQuotaStatus): QuotaVisualState {
  if (quota.blocked_reason === "customer_opted_out") {
    return { state: "opted_out" };
  }

  if (
    quota.blocked_reason === "monthly_quota_reached" &&
    quota.cap_policy === "hard"
  ) {
    return {
      state: "blocked_hard",
      used: quota.used_segments,
      included: quota.included_segments,
    };
  }

  if (quota.remaining_segments === 0 && quota.cap_policy === "soft") {
    return {
      state: "blocked_soft",
      used: quota.used_segments,
      included: quota.included_segments,
    };
  }

  if (
    quota.remaining_segments > 0 &&
    quota.remaining_segments / quota.included_segments <= 0.2
  ) {
    return {
      state: "warning",
      remaining: quota.remaining_segments,
      included: quota.included_segments,
    };
  }

  return {
    state: "normal",
    remaining: quota.remaining_segments,
    included: quota.included_segments,
  };
}
