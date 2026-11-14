/**
 * SmsQuotaIndicator — unit tests
 *
 * Location: packages/ui/src/sms-quota-indicator/SmsQuotaIndicator.test.tsx
 *
 * Tests per design doc G.1.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SmsQuotaIndicator } from "./SmsQuotaIndicator";
import type { SmsQuotaStatus } from "../sms-thread-bubble/types";

const baseQuota: SmsQuotaStatus = {
  period_id: "period-2026-05",
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

describe("SmsQuotaIndicator", () => {
  it("state=normal: renders remaining count in neutral text", () => {
    render(
      <SmsQuotaIndicator
        quota={baseQuota}
        currentMessageSegmentCount={0}
        testID="quota"
      />,
    );
    expect(screen.getByText(/450 segments remaining/i)).toBeTruthy();
  });

  it("state=warning: renders amber ⚠ N segments left", () => {
    const warningQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 420,
      remaining_segments: 80, // 80/500 = 16% < 20%
    };
    render(
      <SmsQuotaIndicator
        quota={warningQuota}
        currentMessageSegmentCount={0}
        testID="quota"
      />,
    );
    expect(screen.getByText(/⚠ 80 segments left/i)).toBeTruthy();
  });

  it("state=blocked_soft: renders fault-color overage-billed message", () => {
    const softQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 500,
      remaining_segments: 0,
      cap_policy: "soft",
    };
    render(
      <SmsQuotaIndicator
        quota={softQuota}
        currentMessageSegmentCount={0}
        testID="quota"
      />,
    );
    expect(screen.getByText(/monthly quota reached.*overage/i)).toBeTruthy();
  });

  it("state=blocked_hard: renders fault-color limit-reached message", () => {
    const hardQuota: SmsQuotaStatus = {
      ...baseQuota,
      used_segments: 500,
      remaining_segments: 0,
      cap_policy: "hard",
      blocked_reason: "monthly_quota_reached",
    };
    render(
      <SmsQuotaIndicator
        quota={hardQuota}
        currentMessageSegmentCount={0}
        testID="quota"
      />,
    );
    expect(screen.getByText(/monthly sms limit reached/i)).toBeTruthy();
  });

  it("state=opted_out: renders opted-out copy", () => {
    const optedOutQuota: SmsQuotaStatus = {
      ...baseQuota,
      blocked_reason: "customer_opted_out",
    };
    render(
      <SmsQuotaIndicator
        quota={optedOutQuota}
        currentMessageSegmentCount={0}
        testID="quota"
      />,
    );
    expect(screen.getByText(/customer has opted out/i)).toBeTruthy();
  });

  it("currentMessageSegmentCount updates preview in real-time for normal state", () => {
    render(
      <SmsQuotaIndicator
        quota={baseQuota}
        currentMessageSegmentCount={3}
        testID="quota"
      />,
    );
    expect(screen.getByText(/this message: 3/i)).toBeTruthy();
  });

  it("isLoading: renders loading text", () => {
    render(
      <SmsQuotaIndicator
        quota={baseQuota}
        currentMessageSegmentCount={0}
        isLoading
        testID="quota"
      />,
    );
    expect(screen.getByText(/loading quota/i)).toBeTruthy();
  });
});
