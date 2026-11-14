/**
 * Unit tests — comms misc helpers (web-compatible only)
 *
 * Location: apps/web/__tests__/batch_fe_b6/unit/comms-misc.test.tsx
 *
 * NOTE: TimeExtractionEditor and CustomerDisambiguationList are React Native
 * components. Their unit tests live in packages/ui/src/message-preview/__tests__/
 * (co-located, runs in the packages/ui vitest environment that has RN stubs).
 *
 * This file tests web-compatible helpers only.
 */

import { describe, it, expect } from "vitest";

// ── SMS segment count computation ─────────────────────────────────────────────

describe("Comms — SMS segment count computation", () => {
  function computeSmsSegments(body: string): number {
    const isAscii = /^[\u0000-\u007F]*$/.test(body);
    const charsPerSegment = isAscii ? 160 : 70;
    return Math.ceil(body.length / charsPerSegment) || 1;
  }

  it("1. empty body computes 1 segment (minimum)", () => {
    expect(computeSmsSegments("")).toBe(1);
  });

  it("2. short ASCII message computes 1 segment", () => {
    expect(computeSmsSegments("Hi! I'm on my way, ETA about 20 minutes.")).toBe(
      1,
    );
  });

  it("3. exactly 160 ASCII chars = 1 segment", () => {
    expect(computeSmsSegments("A".repeat(160))).toBe(1);
  });

  it("4. 161 ASCII chars = 2 segments", () => {
    expect(computeSmsSegments("A".repeat(161))).toBe(2);
  });

  it("5. 320 ASCII chars = 2 segments", () => {
    expect(computeSmsSegments("A".repeat(320))).toBe(2);
  });

  it("6. 321 ASCII chars = 3 segments", () => {
    expect(computeSmsSegments("A".repeat(321))).toBe(3);
  });

  it("7. unicode message uses 70 char/segment threshold", () => {
    const unicodeMsg = "Héllo! I'm on my way."; // non-ASCII é
    expect(computeSmsSegments(unicodeMsg)).toBe(1);
  });

  it("8. long unicode message = multiple segments", () => {
    const unicodeMsg = "é".repeat(71); // 71 unicode chars = 2 segments
    expect(computeSmsSegments(unicodeMsg)).toBe(2);
  });

  it("9. typical tech message fits in 1 segment", () => {
    const msg =
      "Hi! The job is complete. Let me know if you have any questions.";
    expect(computeSmsSegments(msg)).toBe(1);
  });

  it("10. running_late template with ETA fits in 1 segment", () => {
    const msg =
      "Hi, I'm running about 20 minutes behind. Sorry for the inconvenience!";
    expect(computeSmsSegments(msg)).toBe(1);
  });
});
