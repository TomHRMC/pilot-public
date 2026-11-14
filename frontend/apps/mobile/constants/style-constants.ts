/**
 * Mobile style constants
 *
 * Location: apps/mobile/constants/style-constants.ts
 *
 * Derives typed React Native style values from design tokens.
 * Isolates all TypeScript type coercions to one place so StyleSheet
 * definitions never contain raw casts or hardcoded values.
 *
 * All values MUST derive from tokens — no literals allowed.
 */

import type { TextStyle } from "react-native";
import { tokens } from "@pilot/ui/tokens";

// React Native fontWeight requires string literal type, but tokens store numbers.
// Single cast here; all consumers reference `fontWeights` from this module.
type FontWeight = TextStyle["fontWeight"];

export const fontWeights: Record<keyof typeof tokens.fontWeights, FontWeight> =
  Object.fromEntries(
    Object.entries(tokens.fontWeights).map(([k, v]) => [k, String(v)]),
  ) as Record<keyof typeof tokens.fontWeights, FontWeight>;

// Re-export tokens for convenience in StyleSheet files
export { tokens };
