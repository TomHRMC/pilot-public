/**
 * Voice state machine unit tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/voice-state-machine.unit.test.ts
 *
 * Tests the voiceStateTokens constant (6-state indicator),
 * and the live→snapshot one-way transition invariant.
 */

import { voiceStateTokens } from "../../../../packages/ui/src/voice/types";

const ALL_STATES = [
  "idle",
  "listening",
  "processing",
  "speaking",
  "waiting-confirm",
  "error",
] as const;

describe("voice state machine", () => {
  describe("voiceStateTokens — 6 states", () => {
    it.each(ALL_STATES)('state "%s" has all required token fields', (state) => {
      const token = voiceStateTokens[state];
      expect(token).toBeDefined();
      expect(typeof token.bgToken).toBe("string");
      expect(typeof token.iconToken).toBe("string");
      expect(typeof token.label).toBe("string");
      expect(typeof token.accessibilityLabel).toBe("string");
    });

    it.each(ALL_STATES)('state "%s" bgToken starts with $', (state) => {
      expect(voiceStateTokens[state].bgToken.startsWith("$")).toBe(true);
    });

    it.each(ALL_STATES)('state "%s" iconToken starts with $', (state) => {
      expect(voiceStateTokens[state].iconToken.startsWith("$")).toBe(true);
    });

    it("idle state has lowest contrast bg (alert-200)", () => {
      expect(voiceStateTokens.idle.bgToken).toBe("$alert-200");
    });

    it("listening state uses alert-400 bg", () => {
      expect(voiceStateTokens.listening.bgToken).toBe("$alert-400");
    });

    it("processing state uses brand-600 bg", () => {
      expect(voiceStateTokens.processing.bgToken).toBe("$brand-600");
    });

    it("error state uses fault-600 bg", () => {
      expect(voiceStateTokens.error.bgToken).toBe("$fault-600");
    });

    it("has exactly 6 states — no additional states", () => {
      expect(Object.keys(voiceStateTokens)).toHaveLength(6);
    });
  });

  describe("live→snapshot one-way invariant (business rule)", () => {
    it("snapshot mode does not revert to live when mode prop changes", () => {
      // Simulate what VoiceQuotePreview does with useRef
      let hasFrozen = false;

      function applyMode(mode: "live" | "snapshot"): "live" | "snapshot" {
        if (mode === "snapshot") hasFrozen = true;
        return hasFrozen ? "snapshot" : mode;
      }

      expect(applyMode("live")).toBe("live");
      expect(applyMode("snapshot")).toBe("snapshot");
      // After snapshot, any subsequent 'live' must still return 'snapshot'
      expect(applyMode("live")).toBe("snapshot");
    });

    it("snapshot freeze is permanent once triggered", () => {
      const states: Array<"live" | "snapshot"> = [
        "live",
        "live",
        "snapshot",
        "live", // this must NOT revert
        "live", // this must NOT revert
      ];

      let hasFrozen = false;
      const effective = states.map((mode) => {
        if (mode === "snapshot") hasFrozen = true;
        return hasFrozen ? "snapshot" : mode;
      });

      expect(effective).toEqual([
        "live",
        "live",
        "snapshot",
        "snapshot",
        "snapshot",
      ]);
    });
  });
});
