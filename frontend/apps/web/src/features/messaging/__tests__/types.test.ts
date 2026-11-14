/**
 * C-B9 Unit Tests — Messaging Types Utility Functions
 *
 * Location: apps/web/src/features/messaging/__tests__/types.test.ts
 *
 * Tests the utility functions in types.ts: formatMillicentsAsUSD,
 * formatMillicentsPerSegment, formatPhoneNumber, getErrorVariant.
 */

import { describe, it, expect } from "vitest";
import {
  formatMillicentsAsUSD,
  formatMillicentsPerSegment,
  formatPhoneNumber,
  getErrorVariant,
  POLLING_STATUSES,
  TERMINAL_STATUSES,
} from "../types";

describe("formatMillicentsAsUSD", () => {
  it("formats $4.00 correctly", () => {
    expect(formatMillicentsAsUSD(400000)).toBe("$4.00");
  });

  it("formats $0.30 correctly", () => {
    expect(formatMillicentsAsUSD(30000)).toBe("$0.30");
  });

  it("formats $0.00 correctly", () => {
    expect(formatMillicentsAsUSD(0)).toBe("$0.00");
  });

  it("formats $13.37 correctly", () => {
    expect(formatMillicentsAsUSD(1337000)).toBe("$13.37");
  });
});

describe("formatMillicentsPerSegment", () => {
  it("formats $0.003/segment correctly", () => {
    expect(formatMillicentsPerSegment(300)).toBe("$0.003/segment");
  });

  it("formats $0.0031/segment correctly", () => {
    expect(formatMillicentsPerSegment(310)).toBe("$0.003/segment");
  });
});

describe("formatPhoneNumber", () => {
  it("formats US number with country code", () => {
    expect(formatPhoneNumber("+13025551234")).toBe("(302) 555-1234");
  });

  it("formats US number without country code", () => {
    expect(formatPhoneNumber("3025551234")).toBe("(302) 555-1234");
  });

  it("returns empty string for null", () => {
    expect(formatPhoneNumber(null)).toBe("");
  });

  it("returns original string for unrecognized format", () => {
    expect(formatPhoneNumber("+441234567890")).toBe("+441234567890");
  });
});

describe("getErrorVariant", () => {
  it("returns payment_failed for payment_failed status", () => {
    expect(getErrorVariant("payment_failed")).toBe("payment_failed");
  });

  it("returns rejected for brand_rejected", () => {
    expect(getErrorVariant("brand_rejected")).toBe("rejected");
  });

  it("returns rejected for campaign_rejected", () => {
    expect(getErrorVariant("campaign_rejected")).toBe("rejected");
  });

  it("returns suspended for suspended", () => {
    expect(getErrorVariant("suspended")).toBe("suspended");
  });

  it("returns null for non-error statuses", () => {
    expect(getErrorVariant("quoting")).toBeNull();
    expect(getErrorVariant("active")).toBeNull();
    expect(getErrorVariant("awaiting_otp")).toBeNull();
  });
});

describe("POLLING_STATUSES", () => {
  it("includes brand_submitted", () => {
    expect(POLLING_STATUSES.has("brand_submitted")).toBe(true);
  });

  it("includes awaiting_otp", () => {
    expect(POLLING_STATUSES.has("awaiting_otp")).toBe(true);
  });

  it("includes awaiting_number_selection", () => {
    expect(POLLING_STATUSES.has("awaiting_number_selection")).toBe(true);
  });

  it("does not include active (terminal)", () => {
    expect(POLLING_STATUSES.has("active")).toBe(false);
  });
});

describe("TERMINAL_STATUSES", () => {
  it("includes active", () => {
    expect(TERMINAL_STATUSES.has("active")).toBe(true);
  });

  it("includes brand_rejected", () => {
    expect(TERMINAL_STATUSES.has("brand_rejected")).toBe(true);
  });

  it("does not include brand_submitted (pending)", () => {
    expect(TERMINAL_STATUSES.has("brand_submitted")).toBe(false);
  });
});
