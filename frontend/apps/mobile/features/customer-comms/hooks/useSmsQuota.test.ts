/**
 * useSmsQuota — unit tests (including deriveQuotaState)
 *
 * Location: apps/mobile/features/customer-comms/hooks/useSmsQuota.test.ts
 *
 * Tests per design doc G.1.
 */

import { deriveQuotaState } from "@pilot/ui";
import type { SmsQuotaStatus } from "@pilot/ui";

const baseQuota: SmsQuotaStatus = {
  period_id: "p1",
  used_segments: 50,
  included_segments: 500,
  remaining_segments: 450,
  overage_segments: 0,
  cap_policy: "soft",
  period_start: "2026-05-01",
  period_end: "2026-05-31",
  blocked_reason: null,
  projected_month_end_segments: 80,
};

describe("deriveQuotaState — all five visual states", () => {
  it("normal state: remaining > 20% of included", () => {
    const state = deriveQuotaState(baseQuota);
    expect(state.state).toBe("normal");
    if (state.state === "normal") {
      expect(state.remaining).toBe(450);
      expect(state.included).toBe(500);
    }
  });

  it("warning state: remaining ≤ 20% of included (80/500 = 16%)", () => {
    const warningQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 420,
      remaining_segments: 80,
    };
    const state = deriveQuotaState(warningQuota);
    expect(state.state).toBe("warning");
    if (state.state === "warning") {
      expect(state.remaining).toBe(80);
    }
  });

  it("warning boundary: remaining = exactly 20% (100/500)", () => {
    const warningQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 400,
      remaining_segments: 100,
    };
    const state = deriveQuotaState(warningQuota);
    expect(state.state).toBe("warning");
  });

  it("normal: remaining > 20% (101/500 = 20.2%)", () => {
    const almostWarn: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 399,
      remaining_segments: 101,
    };
    const state = deriveQuotaState(almostWarn);
    expect(state.state).toBe("normal");
  });

  it("blocked_hard state: monthly_quota_reached + hard cap", () => {
    const hardQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 500,
      remaining_segments: 0,
      cap_policy: "hard",
      blocked_reason: "monthly_quota_reached",
    };
    const state = deriveQuotaState(hardQuota);
    expect(state.state).toBe("blocked_hard");
    if (state.state === "blocked_hard") {
      expect(state.used).toBe(500);
      expect(state.included).toBe(500);
    }
  });

  it("blocked_soft state: remaining=0 + soft cap", () => {
    const softQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 500,
      remaining_segments: 0,
      cap_policy: "soft",
    };
    const state = deriveQuotaState(softQuota);
    expect(state.state).toBe("blocked_soft");
  });

  it("opted_out state: blocked_reason=customer_opted_out", () => {
    const optedOutQuota: SmsQuotaStatus = {
      ...baseQuota,
      blocked_reason: "customer_opted_out",
    };
    const state = deriveQuotaState(optedOutQuota);
    expect(state.state).toBe("opted_out");
  });

  it("opted_out takes priority over hard cap", () => {
    const bothBlocked: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 500,
      remaining_segments: 0,
      cap_policy: "hard",
      blocked_reason: "customer_opted_out",
    };
    const state = deriveQuotaState(bothBlocked);
    expect(state.state).toBe("opted_out");
  });
});
