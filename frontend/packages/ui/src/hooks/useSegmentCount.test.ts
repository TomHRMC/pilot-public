/**
 * useSegmentCount — unit tests
 *
 * Location: packages/ui/src/hooks/useSegmentCount.test.ts
 *
 * Critical tests per design doc G.1:
 *   - GSM-7 boundary at 160 chars
 *   - Unicode trigger at first non-GSM7 char
 *   - Emoji forces Unicode
 *   - Multi-segment fragmentation boundary (153 chars GSM7 part 2 of 2)
 *
 * Uses computeSegments() (pure function) directly — no React hook boilerplate needed.
 */

import { describe, it, expect } from "vitest";
import { computeSegments } from "./useSegmentCount";

describe("computeSegments — GSM-7 encoding", () => {
  it("empty string → segmentCount=1, charCount=0, encoding=gsm7", () => {
    const result = computeSegments("");
    expect(result.segmentCount).toBe(1);
    expect(result.charCount).toBe(0);
    expect(result.encoding).toBe("gsm7");
    expect(result.charsPerSegment).toBe(160);
    expect(result.charsRemaining).toBe(160);
  });

  it("single GSM-7 segment: 160 chars → segmentCount=1, encoding=gsm7", () => {
    const body = "A".repeat(160);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(1);
    expect(result.encoding).toBe("gsm7");
    expect(result.charCount).toBe(160);
    expect(result.charsPerSegment).toBe(160);
    expect(result.charsRemaining).toBe(0);
  });

  it("GSM-7 boundary: 161 chars → segmentCount=2, charsPerSegment=153", () => {
    const body = "A".repeat(161);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(2);
    expect(result.encoding).toBe("gsm7");
    expect(result.charsPerSegment).toBe(153);
    // 161 chars in 2-segment mode: 161 % 153 = 8, so 153 - 8 = 145 remaining
    expect(result.charsRemaining).toBe(153 - 8);
  });

  it("multi-segment GSM-7: 306 chars → segmentCount=2 (306/153 = 2 exact)", () => {
    const body = "A".repeat(306);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(2);
    expect(result.encoding).toBe("gsm7");
    expect(result.charCount).toBe(306);
    expect(result.charsRemaining).toBe(0); // exactly fills 2 segments
  });

  it("multi-segment GSM-7: 307 chars → segmentCount=3", () => {
    const body = "A".repeat(307);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(3);
    expect(result.encoding).toBe("gsm7");
  });

  it("extended GSM-7 char € counts as 2 code units — stays GSM-7", () => {
    // €€ = 4 code units; 78 × € = 156 code units (under 160) → 1 segment
    const body = "€".repeat(78);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(1);
    expect(result.encoding).toBe("gsm7");
  });

  it("extended GSM-7: 80 × € = 160 code units → exactly 1 segment", () => {
    const body = "€".repeat(80);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(1);
    expect(result.encoding).toBe("gsm7");
    expect(result.charsRemaining).toBe(0);
  });

  it("extended GSM-7: 81 × € = 162 code units → 2 segments", () => {
    const body = "€".repeat(81);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(2);
    expect(result.encoding).toBe("gsm7");
  });

  it("basic ASCII-only message is GSM-7", () => {
    const body = "Hi John, your quote is ready. Call us at (555) 123-4567.";
    const result = computeSegments(body);
    expect(result.encoding).toBe("gsm7");
    expect(result.segmentCount).toBe(1);
  });

  it("newline (\\n) is GSM-7 basic charset", () => {
    const body = "Line one\nLine two";
    const result = computeSegments(body);
    expect(result.encoding).toBe("gsm7");
  });

  it("charsRemaining correct at mid-single-segment", () => {
    const body = "A".repeat(100);
    const result = computeSegments(body);
    expect(result.charsRemaining).toBe(60); // 160 - 100
    expect(result.segmentCount).toBe(1);
  });

  it("charsRemaining correct at exact multi-segment boundary (153 chars)", () => {
    // 153 chars = exactly 1 segment of a 2-part message
    // (trigger multi-segment by having > 160 chars, then this segment is full)
    const body = "A".repeat(153);
    // Under 160 → still single segment
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(1);
    expect(result.charsRemaining).toBe(7); // 160 - 153
  });
});

describe("computeSegments — Unicode encoding", () => {
  it("single Unicode segment: 70 chars with emoji → segmentCount=1, encoding=unicode", () => {
    const body = "😀".repeat(70);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(1);
    expect(result.encoding).toBe("unicode");
    expect(result.charsPerSegment).toBe(70);
    expect(result.charsRemaining).toBe(0);
  });

  it("Unicode boundary: 71 chars → segmentCount=2, charsPerSegment=67", () => {
    const body = "😀".repeat(71);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(2);
    expect(result.encoding).toBe("unicode");
    expect(result.charsPerSegment).toBe(67);
  });

  it("first non-GSM7 char forces unicode encoding", () => {
    // ü is NOT in the GSM-7 charset (ü is, but Chinese character isn't)
    const body = "Hello 你好";
    const result = computeSegments(body);
    expect(result.encoding).toBe("unicode");
  });

  it("emoji forces unicode encoding", () => {
    const body = "Call me! 😊";
    const result = computeSegments(body);
    expect(result.encoding).toBe("unicode");
  });

  it("mixed ASCII + emoji → encoding=unicode", () => {
    const body = "Hi! 🔥 Your job is done.";
    const result = computeSegments(body);
    expect(result.encoding).toBe("unicode");
  });

  it("unicode multi-segment: 134 chars → segmentCount=2 (134/67 = 2 exact)", () => {
    const body = "😀".repeat(134);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(2);
    expect(result.encoding).toBe("unicode");
    expect(result.charCount).toBe(134);
    expect(result.charsRemaining).toBe(0);
  });

  it("charsRemaining correct for unicode single segment mid-range", () => {
    const body = "😀".repeat(40);
    const result = computeSegments(body);
    expect(result.segmentCount).toBe(1);
    expect(result.charsRemaining).toBe(30); // 70 - 40
  });
});

describe("computeSegments — GSM-7 special chars", () => {
  it("{ } [ ] ~ \\ | ^ are extended GSM-7 (2 code units each)", () => {
    // Each extended char = 2 units; 80 extended chars = 160 units = 1 segment exactly
    const extendedChars = "{}[]~\\|^";
    // 8 chars × 2 units = 16 units — well within 1 segment
    const result = computeSegments(extendedChars);
    expect(result.encoding).toBe("gsm7");
    expect(result.segmentCount).toBe(1);
  });

  it("mix of basic and extended GSM-7 chars stays GSM-7", () => {
    const body = "Cost: €500 {urgent}";
    const result = computeSegments(body);
    expect(result.encoding).toBe("gsm7");
  });
});
