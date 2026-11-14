/**
 * ESLint Rule: no-hardcoded-design-values
 *
 * Location: packages/eslint-config/rules/no-hardcoded-design-values.ts
 *
 * Enforces Pass 1 token consumption by flagging hardcoded colors, non-grid
 * spacing values, and hardcoded font sizes in component files.
 *
 * Severity: warning (FE-B0); upgraded to error at FE-B1 close.
 *
 * Flags:
 *   - Hex colors (#xxxxxx, #xxx)
 *   - RGB/HSL color functions
 *   - Pixel values not on the 4px spacing grid (padding, margin, gap, etc.)
 *   - Hardcoded fontSize values in JSX style props
 *
 * Allows:
 *   - Tailwind utility classes (strings like "bg-brand-600")
 *   - Values on the 4px grid (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80)
 *   - Zero (0) values
 *   - "100%" / "auto" / "inherit"
 *   - Token references (colors.brand[600], etc.)
 */

import type { Rule } from "eslint";

// 4px grid: multiples of 4 that appear in tokens.ts
const ALLOWED_SPACING_PX = new Set([
  0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80,
]);

// Hex color pattern
const HEX_COLOR_RE = /#([0-9a-fA-F]{3,8})\b/;

// RGB / HSL / OKLCH color functions
const COLOR_FUNC_RE = /\b(rgb|rgba|hsl|hsla|oklch|color)\s*\(/;

// Pixel value pattern — captures the numeric part
const PX_VALUE_RE = /\b(\d+(?:\.\d+)?)px\b/g;

const rule: Rule.RuleModule = {
  meta: {
    type: "suggestion",
    docs: {
      description:
        "Disallow hardcoded design values; use Pass 1 design tokens instead",
      category: "Design System",
      recommended: false,
    },
    schema: [],
    messages: {
      noHardcodedColor:
        'Hardcoded color "{{value}}" detected. Use a Tailwind token class (e.g., bg-brand-600) or a CSS variable from @pilot/ui/styles/globals.css.',
      noHardcodedSpacing:
        'Spacing value "{{value}}" is not on the 4px grid. Use a Tailwind spacing class (e.g., p-4) or a token from packages/ui/src/tokens.ts.',
      noHardcodedFontSize:
        'Hardcoded fontSize "{{value}}" detected. Use a Tailwind text-size class (e.g., text-body, text-h1) from the pilotPreset.',
    },
  },

  create(context) {
    function checkStringForHardcodedValues(node: Rule.Node, value: string) {
      // Check for hex colors
      if (HEX_COLOR_RE.test(value)) {
        context.report({
          node,
          messageId: "noHardcodedColor",
          data: { value: value.match(HEX_COLOR_RE)?.[0] ?? value },
        });
        return;
      }

      // Check for rgb/hsl color functions
      if (COLOR_FUNC_RE.test(value)) {
        context.report({
          node,
          messageId: "noHardcodedColor",
          data: { value },
        });
        return;
      }

      // Check for off-grid pixel values
      const pxMatches = [...value.matchAll(PX_VALUE_RE)];
      for (const match of pxMatches) {
        const num = parseFloat(match[1] ?? "0");
        if (!ALLOWED_SPACING_PX.has(num)) {
          context.report({
            node,
            messageId: "noHardcodedSpacing",
            data: { value: match[0] },
          });
          return;
        }
      }
    }

    return {
      // Check JSX style prop object properties
      'JSXAttribute[name.name="style"] ObjectExpression > Property'(
        node: Rule.Node,
      ) {
        const prop = node as unknown as {
          key: { name?: string };
          value: { type: string; value?: unknown };
        };
        const keyName = prop.key?.name ?? "";
        const val = prop.value;

        // Flag hardcoded fontSize in style objects
        if (
          keyName === "fontSize" &&
          val.type === "Literal" &&
          typeof val.value === "number"
        ) {
          context.report({
            node,
            messageId: "noHardcodedFontSize",
            data: { value: String(val.value) },
          });
          return;
        }

        // Flag hardcoded colors in style objects
        if (
          (keyName === "color" ||
            keyName === "backgroundColor" ||
            keyName === "borderColor") &&
          val.type === "Literal" &&
          typeof val.value === "string"
        ) {
          checkStringForHardcodedValues(node, val.value);
        }
      },

      // Check string literals in general (catches inline style strings and className values)
      Literal(node: Rule.Node) {
        const litNode = node as unknown as {
          value: unknown;
          parent?: { type: string };
        };
        if (typeof litNode.value !== "string") return;

        // Skip import/require paths
        const parent = litNode.parent;
        if (
          parent &&
          (parent.type === "ImportDeclaration" ||
            parent.type === "ExportNamedDeclaration" ||
            parent.type === "CallExpression")
        ) {
          return;
        }

        checkStringForHardcodedValues(node, litNode.value);
      },
    };
  },
};

export default rule;
export { rule as noHardcodedDesignValues };
