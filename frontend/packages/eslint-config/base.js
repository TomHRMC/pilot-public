import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import turboPlugin from "eslint-plugin-turbo";
import tseslint from "typescript-eslint";
import onlyWarn from "eslint-plugin-only-warn";
import { noHardcodedDesignValues } from "./rules/no-hardcoded-design-values.ts";

/**
 * A shared ESLint configuration for the repository.
 *
 * FE-B1: Added pilot/no-hardcoded-design-values at ERROR severity.
 * Promotes design-token discipline across all packages from FE-B1 onward.
 *
 * @type {import("eslint").Linter.Config[]}
 * */
export const config = [
  js.configs.recommended,
  eslintConfigPrettier,
  ...tseslint.configs.recommended,
  {
    plugins: {
      turbo: turboPlugin,
    },
    rules: {
      "turbo/no-undeclared-env-vars": "warn",
    },
  },
  {
    plugins: {
      onlyWarn,
    },
  },
  // ── Pilot design token enforcement (FE-B1) ─────────────────────────────────
  // Applied to all component source files (web). Exempt: token definitions,
  // mobile RN style files (use numeric values), and test files.
  {
    plugins: {
      pilot: {
        rules: {
          "no-hardcoded-design-values": noHardcodedDesignValues,
        },
      },
    },
    files: ["src/**/*.tsx", "src/**/*.ts"],
    ignores: [
      // Token source files ARE the design system — must be exempt
      "**/tokens.ts",
      "**/tailwind.preset.ts",
      "**/globals.css",
      // Test files use string literals in assertions — not component code
      "**/*.test.ts",
      "**/*.test.tsx",
      "**/*.spec.ts",
      "**/*.spec.tsx",
      // NOTE: mobile files are NOT exempt — they must use token imports.
      // React Native style objects must reference mobileFontSizes, fontWeights,
      // spacing, and radii from @pilot/ui/tokens instead of hardcoded numbers.
    ],
    rules: {
      "pilot/no-hardcoded-design-values": "error",
    },
  },
  {
    // Test files: relax display-name requirement for wrapper components
    files: ["**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts", "**/*.spec.tsx"],
    rules: {
      "react/display-name": "off",
    },
  },
  {
    ignores: ["dist/**"],
  },
];
