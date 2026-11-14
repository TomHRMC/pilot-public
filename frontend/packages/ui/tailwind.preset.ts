/**
 * Tailwind v4 Preset — Pilot for Trades Design System
 *
 * Location: packages/ui/tailwind.preset.ts
 *
 * Consumption:
 *   - apps/web/tailwind.config.ts:
 *       import { pilotPreset } from '@pilot/ui/tailwind.preset';
 *       export default { presets: [pilotPreset], content: [...] };
 *   - apps/mobile: does NOT consume this directly; Gluestack-UI reads
 *     tokens from @pilot/ui/tokens at runtime via theme config.
 *
 * Tailwind v4 note:
 *   v4 prefers CSS-first theming via @theme blocks. This preset uses the
 *   JS config path for interop with shadcn/ui's component expectations.
 *   If we move fully to @theme, migrate these mappings to CSS variables
 *   in packages/ui/src/styles/globals.css.
 */

import type { Config } from "tailwindcss";
import { colors, fonts, radii, spacing } from "./src/tokens";

export const pilotPreset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        brand: colors.brand,
        alert: colors.alert,
        margin: colors.margin,
        fault: colors.fault,
        neutral: colors.neutral,

        // Semantic aliases — what shadcn/ui components reference.
        // These resolve to CSS variables at runtime so they flip with theme.
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        secondary: "hsl(var(--secondary))",
        "secondary-foreground": "hsl(var(--secondary-foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        accent: "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",
        destructive: "hsl(var(--destructive))",
        "destructive-foreground": "hsl(var(--destructive-foreground))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },

      fontFamily: {
        sans: fonts.sans.split(", "),
        mono: fonts.mono.split(", "),
      },

      fontSize: {
        caption: ["12px", { lineHeight: "16px" }],
        body: ["14px", { lineHeight: "20px" }],
        "body-lg": ["15px", { lineHeight: "22px" }],
        h3: ["15px", { lineHeight: "22px", fontWeight: "500" }],
        h2: ["18px", { lineHeight: "26px", fontWeight: "500" }],
        h1: ["20px", { lineHeight: "28px", fontWeight: "500" }],
        display: ["26px", { lineHeight: "32px", fontWeight: "500" }],
      },

      fontWeight: {
        normal: "400",
        medium: "500",
      },

      borderRadius: {
        none: `${radii.none}px`,
        sm: `${radii.sm}px`,
        md: `${radii.md}px`,
        lg: `${radii.lg}px`,
        xl: `${radii.xl}px`,
        full: "9999px",
      },

      spacing: Object.fromEntries(
        Object.entries(spacing).map(([k, v]) => [k, `${v}px`]),
      ),

      // Voice state animations
      keyframes: {
        "voice-pulse": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.05)" },
        },
        "voice-dots": {
          "0%, 80%, 100%": { opacity: "0.3" },
          "40%": { opacity: "1" },
        },
      },
      animation: {
        "voice-pulse": "voice-pulse 1.4s ease-in-out infinite",
        "voice-dots": "voice-dots 1.4s ease-in-out infinite",
      },
    },
  },
};

export default pilotPreset;
