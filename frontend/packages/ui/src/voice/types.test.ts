/**
 * Voice types unit tests
 *
 * Location: packages/ui/src/voice/types.test.ts
 *
 * Test plan §I — 4 tests for voiceStateTokens:
 *   1. Has entries for all 6 states
 *   2. Each state entry has all required fields
 *   3. No hardcoded hex values — tokens start with "$"
 *   4. Token names match expected Gluestack token format
 */

import { describe, it, expect } from "vitest";
import { voiceStateTokens } from "./types";
import type { VoiceState } from "./types";

const ALL_STATES: VoiceState[] = [
  "idle",
  "listening",
  "processing",
  "speaking",
  "waiting-confirm",
  "error",
];

describe("voiceStateTokens", () => {
  it("has entries for all 6 voice states", () => {
    for (const state of ALL_STATES) {
      expect(voiceStateTokens).toHaveProperty(state);
    }
    expect(Object.keys(voiceStateTokens)).toHaveLength(6);
  });

  it("each state entry has bgToken, iconToken, label, accessibilityLabel", () => {
    for (const state of ALL_STATES) {
      const entry = voiceStateTokens[state];
      expect(typeof entry.bgToken).toBe("string");
      expect(typeof entry.iconToken).toBe("string");
      expect(typeof entry.label).toBe("string");
      expect(typeof entry.accessibilityLabel).toBe("string");
      expect(entry.label.length).toBeGreaterThan(0);
      expect(entry.accessibilityLabel.length).toBeGreaterThan(0);
    }
  });

  it('no hardcoded hex values — all bgToken and iconToken start with "$"', () => {
    for (const state of ALL_STATES) {
      const { bgToken, iconToken } = voiceStateTokens[state];
      expect(bgToken.startsWith("$")).toBe(true);
      expect(iconToken.startsWith("$")).toBe(true);
    }
  });

  it("token names match expected Gluestack token format ($ramp-stop or $white)", () => {
    const validTokenPattern =
      /^\$(alert|brand|fault|margin|neutral|white)(-\d+)?$/;
    for (const state of ALL_STATES) {
      const { bgToken, iconToken } = voiceStateTokens[state];
      expect(validTokenPattern.test(bgToken)).toBe(true);
      expect(validTokenPattern.test(iconToken)).toBe(true);
    }
  });
});
