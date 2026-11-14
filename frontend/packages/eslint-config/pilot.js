/**
 * Pilot design token enforcement config
 *
 * Location: packages/eslint-config/pilot.js
 *
 * A flat config entry that registers and enforces the pilot/no-hardcoded-design-values rule
 * at ERROR severity. Import this into any app's eslint.config.mjs.
 *
 * Usage:
 *   import { pilotTokenConfig } from "@repo/eslint-config/pilot";
 *   export default defineConfig([...pilotTokenConfig]);
 */

import { noHardcodedDesignValues } from "./rules/no-hardcoded-design-values.ts";

/** Glob patterns that are exempt from token enforcement */
const TOKEN_ENFORCEMENT_IGNORES = [
  // Token source files define raw values — they ARE the source of truth
  "**/tokens.ts",
  "**/tailwind.preset.ts",
  "**/globals.css",
  // Test / spec files use string literals in assertions
  "**/*.test.ts",
  "**/*.test.tsx",
  "**/*.spec.ts",
  "**/*.spec.tsx",
];

/**
 * Flat config array entry for Pilot design token enforcement.
 *
 * Registers the custom ESLint rule and enforces it at ERROR severity across
 * all source files. Import and spread into any Next.js or React Native app config.
 */
export const pilotTokenConfig = [
  {
    plugins: {
      pilot: {
        rules: {
          "no-hardcoded-design-values": noHardcodedDesignValues,
        },
      },
    },
    ignores: TOKEN_ENFORCEMENT_IGNORES,
    rules: {
      "pilot/no-hardcoded-design-values": "error",
    },
  },
];
