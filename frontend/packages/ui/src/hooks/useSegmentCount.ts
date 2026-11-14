/**
 * useSegmentCount — SMS Segment Count Hook
 *
 * Location: packages/ui/src/hooks/useSegmentCount.ts
 * Exported from: packages/ui/src/index.ts under // ── FE-B10 Exports ──
 *
 * Established in FE-B10 (SMS inbound reply composer).
 * Consumed by: apps/mobile/features/customer-comms/components/ReplyComposer.tsx
 *
 * Implements proper GSM-7 charset validation with multi-segment boundaries.
 * The existing computeSmsSegments() in usePreviewBeforeSend.ts is a simplified
 * ASCII heuristic — this hook is the canonical implementation.
 *
 * GSM-7 spec:
 *   - Basic charset: A-Z a-z 0-9 @£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ !"#¤%&'()*+,-./;:<=>?¡ÄÖÑÜ§¿äöñüà
 *   - Extended table (each char = 2 code units): { } [ ] ~ \ | ^ € \f
 *   - Single segment: 160 (GSM-7) | 70 (Unicode)
 *   - Multi-segment UDH: 153 (GSM-7) | 67 (Unicode) per segment
 *
 * RULE 4: Segment count is NEVER hardcoded inline — always use this hook.
 */

import { useMemo } from "react";

// ── GSM-7 charset definitions ─────────────────────────────────────────────────

/**
 * GSM-7 Basic Character Set.
 * Each character here costs 1 GSM-7 code unit.
 */
const GSM7_BASIC_CHARS = new Set([
  "@",
  "£",
  "$",
  "¥",
  "è",
  "é",
  "ù",
  "ì",
  "ò",
  "Ç",
  "\n",
  "Ø",
  "ø",
  "\r",
  "Å",
  "å",
  "Δ",
  "_",
  "Φ",
  "Γ",
  "Λ",
  "Ω",
  "Π",
  "Ψ",
  "Σ",
  "Θ",
  "Ξ",
  " ",
  "!",
  '"',
  "#",
  "¤",
  "%",
  "&",
  "'",
  "(",
  ")",
  "*",
  "+",
  ",",
  "-",
  ".",
  "/",
  "0",
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  ":",
  ";",
  "<",
  "=",
  ">",
  "?",
  "¡",
  "A",
  "B",
  "C",
  "D",
  "E",
  "F",
  "G",
  "H",
  "I",
  "J",
  "K",
  "L",
  "M",
  "N",
  "O",
  "P",
  "Q",
  "R",
  "S",
  "T",
  "U",
  "V",
  "W",
  "X",
  "Y",
  "Z",
  "Ä",
  "Ö",
  "Ñ",
  "Ü",
  "§",
  "¿",
  "a",
  "b",
  "c",
  "d",
  "e",
  "f",
  "g",
  "h",
  "i",
  "j",
  "k",
  "l",
  "m",
  "n",
  "o",
  "p",
  "q",
  "r",
  "s",
  "t",
  "u",
  "v",
  "w",
  "x",
  "y",
  "z",
  "ä",
  "ö",
  "ñ",
  "ü",
  "à",
]);

/**
 * GSM-7 Extended Character Set.
 * Each character here costs 2 GSM-7 code units (escape + char).
 */
const GSM7_EXTENDED_CHARS = new Set([
  "{",
  "}",
  "[",
  "]",
  "~",
  "\\",
  "|",
  "^",
  "€",
  "\f",
]);

// ── Core logic ────────────────────────────────────────────────────────────────

/**
 * Compute the GSM-7 code unit count for a string.
 * Extended chars count as 2 units each.
 * Returns -1 if any character is outside the GSM-7 charset (forces Unicode).
 */
function computeGsm7CodeUnits(body: string): number {
  let units = 0;
  for (const char of body) {
    if (GSM7_BASIC_CHARS.has(char)) {
      units += 1;
    } else if (GSM7_EXTENDED_CHARS.has(char)) {
      units += 2; // escape + char
    } else {
      return -1; // Non-GSM-7 character — force Unicode
    }
  }
  return units;
}

// ── Public types ──────────────────────────────────────────────────────────────

export interface SegmentCountResult {
  /** Number of SMS segments required to deliver this message */
  segmentCount: number;
  /** Character encoding — affects segment boundaries */
  encoding: "gsm7" | "unicode";
  /** Character count (Unicode codepoints) */
  charCount: number;
  /**
   * Chars per segment for the current message length.
   * - GSM-7 single segment: 160
   * - GSM-7 multi-segment (UDH): 153
   * - Unicode single segment: 70
   * - Unicode multi-segment (UDH): 67
   */
  charsPerSegment: number;
  /** Chars remaining until the next segment boundary */
  charsRemaining: number;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * useSegmentCount — real-time SMS segment count hook.
 *
 * @param body — the message body to analyze
 * @returns SegmentCountResult with all segment metadata
 *
 * Memoized via useMemo([body]) — safe to call on every render.
 */
export function useSegmentCount(body: string): SegmentCountResult {
  return useMemo(() => computeSegments(body), [body]);
}

/**
 * computeSegments — pure function for use outside React components (e.g., tests).
 * useSegmentCount wraps this with useMemo.
 */
export function computeSegments(body: string): SegmentCountResult {
  const charCount = [...body].length; // Unicode codepoints (handles emoji correctly)

  if (charCount === 0) {
    return {
      segmentCount: 1,
      encoding: "gsm7",
      charCount: 0,
      charsPerSegment: 160,
      charsRemaining: 160,
    };
  }

  const gsm7Units = computeGsm7CodeUnits(body);
  const isGsm7 = gsm7Units !== -1;

  if (isGsm7) {
    // GSM-7 path — use code unit count
    const singleSegmentLimit = 160;
    const multiSegmentLimit = 153;

    if (gsm7Units <= singleSegmentLimit) {
      return {
        segmentCount: 1,
        encoding: "gsm7",
        charCount,
        charsPerSegment: singleSegmentLimit,
        charsRemaining: singleSegmentLimit - gsm7Units,
      };
    }

    const segmentCount = Math.ceil(gsm7Units / multiSegmentLimit);
    const currentSegmentUsed = gsm7Units % multiSegmentLimit;
    const charsRemaining =
      currentSegmentUsed === 0 ? 0 : multiSegmentLimit - currentSegmentUsed;

    return {
      segmentCount,
      encoding: "gsm7",
      charCount,
      charsPerSegment: multiSegmentLimit,
      charsRemaining,
    };
  }

  // Unicode path — use codepoint count
  const singleSegmentLimit = 70;
  const multiSegmentLimit = 67;

  if (charCount <= singleSegmentLimit) {
    return {
      segmentCount: 1,
      encoding: "unicode",
      charCount,
      charsPerSegment: singleSegmentLimit,
      charsRemaining: singleSegmentLimit - charCount,
    };
  }

  const segmentCount = Math.ceil(charCount / multiSegmentLimit);
  const currentSegmentUsed = charCount % multiSegmentLimit;
  const charsRemaining =
    currentSegmentUsed === 0 ? 0 : multiSegmentLimit - currentSegmentUsed;

  return {
    segmentCount,
    encoding: "unicode",
    charCount,
    charsPerSegment: multiSegmentLimit,
    charsRemaining,
  };
}
