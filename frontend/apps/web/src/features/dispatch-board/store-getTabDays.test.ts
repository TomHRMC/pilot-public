/**
 * getTabDays — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/store-getTabDays.test.ts
 * Per batch-beta-v1-fixes-b5-design.md §I.1
 * Updated FE-B30: removed "4day" tab (DispatchViewTab is now "day"|"week"|"month")
 * Updated UI-Fix: month view now returns actual days in the calendar month.
 *
 * Verifies getTabDays returns the correct day count for all 3 view tabs.
 */

import { describe, it, expect } from "vitest";
import { getTabDays, getDaysInMonth } from "./store";

describe("getTabDays", () => {
  it("day tab returns 1", () => {
    expect(getTabDays("day")).toBe(1);
  });

  it("week tab returns 7", () => {
    expect(getTabDays("week")).toBe(7);
  });

  it("month tab without activeDate returns 31 (default)", () => {
    expect(getTabDays("month")).toBe(31);
  });

  it("month tab with activeDate returns actual days in that month", () => {
    // July 2026 has 31 days
    expect(getTabDays("month", "2026-07-01")).toBe(31);
    // February 2026 (non-leap year) has 28 days
    expect(getTabDays("month", "2026-02-01")).toBe(28);
    // February 2024 (leap year) has 29 days
    expect(getTabDays("month", "2024-02-01")).toBe(29);
    // April 2026 has 30 days
    expect(getTabDays("month", "2026-04-01")).toBe(30);
  });
});

describe("getDaysInMonth", () => {
  it("returns 31 for July 2026", () => {
    expect(getDaysInMonth("2026-07-01")).toBe(31);
  });

  it("returns 28 for February 2026 (non-leap)", () => {
    expect(getDaysInMonth("2026-02-01")).toBe(28);
  });

  it("returns 29 for February 2024 (leap year)", () => {
    expect(getDaysInMonth("2024-02-01")).toBe(29);
  });
});
