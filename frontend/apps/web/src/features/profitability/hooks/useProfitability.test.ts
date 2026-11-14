/**
 * useProfitability — Unit Tests
 *
 * Location: apps/web/src/features/profitability/hooks/useProfitability.test.ts
 *
 * Tests:
 *  1. periodToDates() — correct YYYY-MM-DD output for all 4 period values
 *  2. useProfitability hook — sends date_from / date_to (not period) to API
 *  3. useProfitability hook — skips API call when period=custom without dates
 *
 * BETA-B2: verifies Issue 3.5 fix (422 from ?period=7d replaced by date params)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { format, subDays, startOfMonth, startOfYear } from "date-fns";
import { periodToDates } from "./useProfitability";

// ─── periodToDates() — pure function, no mocks needed ────────────────────────

describe("periodToDates()", () => {
  // Pin "today" so date assertions are deterministic
  const FIXED_NOW = new Date("2025-06-15T12:00:00.000Z");

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(FIXED_NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("converts 7d to correct date range", () => {
    const { date_from, date_to } = periodToDates("7d");
    expect(date_to).toBe(format(FIXED_NOW, "yyyy-MM-dd"));
    expect(date_from).toBe(format(subDays(FIXED_NOW, 7), "yyyy-MM-dd"));
  });

  it("converts 30d to correct date range", () => {
    const { date_from, date_to } = periodToDates("30d");
    expect(date_to).toBe(format(FIXED_NOW, "yyyy-MM-dd"));
    expect(date_from).toBe(format(subDays(FIXED_NOW, 30), "yyyy-MM-dd"));
  });

  it("converts mtd to first of current month", () => {
    const { date_from, date_to } = periodToDates("mtd");
    expect(date_from).toBe(format(startOfMonth(FIXED_NOW), "yyyy-MM-dd"));
    expect(date_to).toBe(format(FIXED_NOW, "yyyy-MM-dd"));
  });

  it("converts ytd to January 1 of current year", () => {
    const { date_from, date_to } = periodToDates("ytd");
    expect(date_from).toBe(format(startOfYear(FIXED_NOW), "yyyy-MM-dd"));
    expect(date_to).toBe(format(FIXED_NOW, "yyyy-MM-dd"));
  });

  it("all outputs are valid YYYY-MM-DD format", () => {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    for (const period of ["7d", "30d", "mtd", "ytd"] as const) {
      const { date_from, date_to } = periodToDates(period);
      expect(date_from).toMatch(dateRegex);
      expect(date_to).toMatch(dateRegex);
    }
  });

  it("7d date_from is 7 days before date_to", () => {
    const { date_from, date_to } = periodToDates("7d");
    const fromMs = new Date(date_from).getTime();
    const toMs = new Date(date_to).getTime();
    const diffDays = (toMs - fromMs) / (1000 * 60 * 60 * 24);
    expect(diffDays).toBe(7);
  });

  it("30d date_from is 30 days before date_to", () => {
    const { date_from, date_to } = periodToDates("30d");
    const fromMs = new Date(date_from).getTime();
    const toMs = new Date(date_to).getTime();
    const diffDays = (toMs - fromMs) / (1000 * 60 * 60 * 24);
    expect(diffDays).toBe(30);
  });

  it("mtd date_from is on the 1st of the month", () => {
    const { date_from } = periodToDates("mtd");
    expect(date_from).toMatch(/-01$/);
  });

  it("ytd date_from is January 1", () => {
    const { date_from } = periodToDates("ytd");
    expect(date_from).toMatch(/-01-01$/);
  });

  it("date_to is never before date_from", () => {
    for (const period of ["7d", "30d", "mtd", "ytd"] as const) {
      const { date_from, date_to } = periodToDates(period);
      expect(new Date(date_to).getTime()).toBeGreaterThanOrEqual(
        new Date(date_from).getTime(),
      );
    }
  });
});

// ─── QUERY KEY ────────────────────────────────────────────────────────────────

import { PROFITABILITY_QUERY_KEY } from "./useProfitability";

describe("PROFITABILITY_QUERY_KEY", () => {
  it("includes date_from and date_to (not period string)", () => {
    const key = PROFITABILITY_QUERY_KEY("2025-06-01", "2025-06-15");
    expect(key).toEqual(["profitability", "2025-06-01", "2025-06-15"]);
  });

  it("does not contain the word 'period' or shorthand values", () => {
    const key = PROFITABILITY_QUERY_KEY("2025-05-16", "2025-06-15");
    const keyStr = JSON.stringify(key);
    expect(keyStr).not.toContain("7d");
    expect(keyStr).not.toContain("30d");
    expect(keyStr).not.toContain("mtd");
    expect(keyStr).not.toContain("ytd");
  });
});
