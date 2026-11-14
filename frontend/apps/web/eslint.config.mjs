import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import { pilotTokenConfig } from "@repo/eslint-config/pilot";

/**
 * ESLint configuration for apps/web (Next.js)
 *
 * Extends Next.js recommended config with the Pilot design token enforcement rule.
 * pilot/no-hardcoded-design-values enforces Pass 1 token consumption across all
 * surface-level components — every color, spacing, and fontSize must reference
 * tokens from @pilot/ui/tokens rather than hardcoded values.
 */
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  // ── Pilot design token enforcement ────────────────────────────────────────
  ...pilotTokenConfig,
]);

export default eslintConfig;
