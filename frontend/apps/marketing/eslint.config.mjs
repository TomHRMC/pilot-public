import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import { pilotTokenConfig } from "@repo/eslint-config/pilot";

/**
 * ESLint configuration for apps/marketing (Next.js)
 *
 * Identical token enforcement rules as apps/web — all design values must
 * reference tokens from @pilot/ui/tokens, no hardcoded hex codes, px values
 * outside the 4px grid, or raw font-size numbers in any component.
 */
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  // ── Pilot design token enforcement ────────────────────────────────────────
  ...pilotTokenConfig,
]);

export default eslintConfig;
