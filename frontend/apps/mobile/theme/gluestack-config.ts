/**
 * Gluestack-UI Theme — AevoFab Mobile
 *
 * Location: apps/mobile/theme/gluestack-config.ts
 *
 * Purpose:
 *   Maps AevoFab design tokens to Gluestack-UI's theme config format.
 *   Mobile defaults to dark theme; honors prefers-color-scheme.
 *
 * Consumption:
 *   apps/mobile/app/_layout.tsx:
 *     import { GluestackUIProvider } from '@gluestack-ui/themed';
 *     import { aevofabConfig } from '@/theme/gluestack-config';
 *     <GluestackUIProvider config={aevofabConfig} colorMode={colorMode}>
 */

import { createConfig } from "@gluestack-ui/themed";
import {
  colors,
  mobileFontSizes,
  mobileLineHeights,
  fonts,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";

export const pilotConfig = createConfig({
  aliases: {
    bg: "backgroundColor",
    color: "color",
    p: "padding",
    px: "paddingHorizontal",
    py: "paddingVertical",
    m: "margin",
    mx: "marginHorizontal",
    my: "marginVertical",
  },
  tokens: {
    colors: {
      // Ramp colors
      brand50: colors.brand[50],
      brand100: colors.brand[100],
      brand200: colors.brand[200],
      brand400: colors.brand[400],
      brand600: colors.brand[600],
      brand800: colors.brand[800],
      brand900: colors.brand[900],

      alert50: colors.alert[50],
      alert100: colors.alert[100],
      alert200: colors.alert[200],
      alert400: colors.alert[400],
      alert600: colors.alert[600],
      alert800: colors.alert[800],
      alert900: colors.alert[900],

      margin50: colors.margin[50],
      margin100: colors.margin[100],
      margin200: colors.margin[200],
      margin400: colors.margin[400],
      margin600: colors.margin[600],
      margin800: colors.margin[800],
      margin900: colors.margin[900],

      fault50: colors.fault[50],
      fault100: colors.fault[100],
      fault200: colors.fault[200],
      fault400: colors.fault[400],
      fault600: colors.fault[600],
      fault800: colors.fault[800],
      fault900: colors.fault[900],

      neutral50: colors.neutral[50],
      neutral100: colors.neutral[100],
      neutral200: colors.neutral[200],
      neutral400: colors.neutral[400],
      neutral600: colors.neutral[600],
      neutral800: colors.neutral[800],
      neutral900: colors.neutral[900],

      // Dark-theme semantic defaults (mobile-first)
      backgroundPrimary: colors.neutral[900],
      backgroundSecondary: colors.neutral[800],
      textPrimary: colors.neutral[50],
      textSecondary: colors.neutral[200],
      textTertiary: colors.neutral[400],

      primary: colors.brand[400], // Lighter brand on dark
      primaryHover: colors.brand[200],
      primaryText: colors.neutral[900],

      success: colors.margin[400],
      warning: colors.alert[400],
      danger: colors.fault[400],
    },

    space: Object.fromEntries(Object.entries(spacing).map(([k, v]) => [k, v])),

    fonts: {
      body: fonts.sans,
      heading: fonts.sans,
      mono: fonts.mono,
    },

    fontSizes: mobileFontSizes,
    lineHeights: mobileLineHeights,
    fontWeights: {
      normal: fontWeights.regular,
      medium: fontWeights.medium,
    },

    radii,

    // Touch target tokens — use for buttons, pressable areas
    sizes: {
      touchSm: touchTargets.mobile.sm,
      touchMd: touchTargets.mobile.md,
      touchLg: touchTargets.mobile.lg,
    },
  },
});

export type PilotConfig = typeof pilotConfig;
