/**
 * AevoFab Design Tokens — Pass 1
 *
 * Single source of truth for colors, typography, spacing, and motion across
 * apps/web (Next.js + shadcn/ui) and apps/mobile (Expo + Gluestack-UI).
 *
 * Location: packages/ui/src/tokens.ts
 *
 * Consumption:
 *   - Web: imported by tailwind.config.ts preset in packages/ui
 *   - Mobile: imported by Gluestack theme config in apps/mobile
 *   - Runtime: imported directly for inline styles and dynamic theming
 *
 * Naming convention:
 *   All ramps are trade-neutral. Semantic meaning is encoded in the name
 *   (brand, alert, margin, fault, neutral) so a plumber or HVAC technician
 *   reading the codebase sees vocabulary that applies to their domain.
 */

// ---------------------------------------------------------------------------
// Color ramps — 7 stops per ramp, Tailwind 50–900 convention
// ---------------------------------------------------------------------------

export const colors = {
  /** Primary brand. CTAs, links, active nav, voltage-indigo. */
  brand: {
    50: "#EEF1FF",
    100: "#D6DCFF",
    200: "#ADB8FF",
    400: "#6875F5",
    600: "#3B43D6", // Default brand stop
    800: "#232AA3",
    900: "#181D66",
  },

  /** Voice-active state, NEC/code warnings, attention-needed. */
  alert: {
    50: "#FFF7EB",
    100: "#FEEBC8",
    200: "#FDD997",
    400: "#F59E0B", // Voice listening pulse
    600: "#B45309", // NEC warning text
    800: "#78350F",
    900: "#451A03",
  },

  /** Profit, success, on-budget, job-completed. */
  margin: {
    50: "#ECFDF5",
    100: "#D1FAE5",
    200: "#A7F3D0",
    400: "#34D399",
    600: "#059669", // Default success stop
    800: "#065F46",
    900: "#022C22",
  },

  /** Over-budget, overdue, errors, live-wire danger. */
  fault: {
    50: "#FEF2F2",
    100: "#FEE2E2",
    200: "#FECACA",
    400: "#F87171",
    600: "#DC2626", // Default error stop
    800: "#991B1B",
    900: "#450A0A",
  },

  /** Neutrals. Text, surfaces, borders. Warm stone, not cool gray. */
  neutral: {
    50: "#FAFAF9",
    100: "#F5F5F4",
    200: "#E7E5E4",
    400: "#A8A29E",
    600: "#57534E",
    800: "#292524",
    900: "#1C1917",
  },
} as const;

// ---------------------------------------------------------------------------
// Semantic color mappings — what UI code should reference
// ---------------------------------------------------------------------------

/**
 * Light theme — default for web, optional for mobile.
 * Dense data surfaces, office lighting, mouse-precision targets.
 */
export const lightTheme = {
  background: {
    primary: colors.neutral[50], // Page background
    secondary: "#FFFFFF", // Card / raised surface
    tertiary: colors.neutral[100], // Subtle inset (table stripe, input bg)
  },
  text: {
    primary: colors.neutral[900], // Body copy, headings
    secondary: colors.neutral[600], // Meta, captions, placeholder
    tertiary: colors.neutral[400], // Disabled, hints
    inverse: colors.neutral[50], // Text on dark surfaces
  },
  border: {
    subtle: colors.neutral[200],
    default: colors.neutral[400],
    strong: colors.neutral[600],
  },
  brand: {
    bg: colors.brand[600], // Button fill
    bgHover: colors.brand[800],
    bgMuted: colors.brand[50], // Subtle brand background
    text: "#FFFFFF", // Text on brand bg
    textOnMuted: colors.brand[800], // Text on brand[50]
  },
  success: {
    bg: colors.margin[600],
    bgMuted: colors.margin[50],
    text: "#FFFFFF",
    textOnMuted: colors.margin[800],
  },
  warning: {
    bg: colors.alert[400],
    bgMuted: colors.alert[50],
    text: colors.alert[900],
    textOnMuted: colors.alert[800],
  },
  danger: {
    bg: colors.fault[600],
    bgMuted: colors.fault[50],
    text: "#FFFFFF",
    textOnMuted: colors.fault[800],
  },
} as const;

/**
 * Dark theme — default for mobile, optional for web.
 * Outdoor lighting, job sites, high-contrast requirements.
 */
export const darkTheme = {
  background: {
    primary: colors.neutral[900], // Page background
    secondary: colors.neutral[800], // Card / raised surface
    tertiary: "#353130", // Subtle inset
  },
  text: {
    primary: colors.neutral[50],
    secondary: colors.neutral[200],
    tertiary: colors.neutral[400],
    inverse: colors.neutral[900],
  },
  border: {
    subtle: colors.neutral[800],
    default: colors.neutral[600],
    strong: colors.neutral[400],
  },
  brand: {
    bg: colors.brand[400], // Lighter on dark for contrast
    bgHover: colors.brand[200],
    bgMuted: colors.brand[900],
    text: colors.neutral[900], // Dark text on brand[400]
    textOnMuted: colors.brand[100],
  },
  success: {
    bg: colors.margin[400],
    bgMuted: colors.margin[900],
    text: colors.neutral[900],
    textOnMuted: colors.margin[100],
  },
  warning: {
    bg: colors.alert[400],
    bgMuted: colors.alert[900],
    text: colors.alert[900],
    textOnMuted: colors.alert[100],
  },
  danger: {
    bg: colors.fault[400],
    bgMuted: colors.fault[900],
    text: colors.neutral[900],
    textOnMuted: colors.fault[100],
  },
} as const;

// ---------------------------------------------------------------------------
// Typography
// ---------------------------------------------------------------------------

export const fonts = {
  sans: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace',
} as const;

/**
 * Type scale — web (dense dashboard).
 * Pair with line heights in the same-index `webLineHeights`.
 */
export const webFontSizes = {
  caption: 11, // Meta, timestamps
  body: 13, // Default body copy
  bodyLg: 15, // Prominent body / form labels
  h3: 15,
  h2: 18,
  h1: 20,
  display: 26, // Dashboard headline numbers
} as const;

export const webLineHeights = {
  caption: 16,
  body: 20,
  bodyLg: 22,
  h3: 22,
  h2: 26,
  h1: 28,
  display: 32,
} as const;

/**
 * Type scale — mobile (field tech).
 * Defaults ~2px larger than web; designed for glove-distance reading.
 */
export const mobileFontSizes = {
  caption: 11,
  body: 13,
  bodyLg: 15,
  h3: 17,
  h2: 20,
  h1: 22,
  display: 28,
} as const;

export const mobileLineHeights = {
  caption: 16,
  body: 20,
  bodyLg: 22,
  h3: 24,
  h2: 28,
  h1: 30,
  display: 36,
} as const;

/**
 * Font weights. Two weights only — regular and medium.
 * No 600/700/bold. Heavy weights make Inter look aggressive on data surfaces.
 */
export const fontWeights = {
  regular: 400,
  medium: 500,
} as const;

// ---------------------------------------------------------------------------
// Spacing — 4px grid
// ---------------------------------------------------------------------------

export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
  20: 80,
} as const;

// ---------------------------------------------------------------------------
// Touch targets — platform-differentiated
// ---------------------------------------------------------------------------

/**
 * Touch target minimums by platform.
 * Mobile 56px is deliberate: Mike wears work gloves. 44pt iOS default is
 * insufficient for field conditions.
 */
export const touchTargets = {
  web: {
    sm: 28,
    md: 36, // Default web button
    lg: 44,
  },
  tablet: {
    sm: 36,
    md: 48, // Default tablet button
    lg: 56,
  },
  mobile: {
    sm: 44,
    md: 56, // Default mobile button — glove-friendly
    lg: 64, // Primary voice action
  },
} as const;

// ---------------------------------------------------------------------------
// Border radius
// ---------------------------------------------------------------------------

export const radii = {
  none: 0,
  sm: 6,
  md: 8, // Default for buttons, inputs, small cards
  lg: 12, // Default for cards
  xl: 16,
  full: 9999,
} as const;

// ---------------------------------------------------------------------------
// Voice state machine — canonical six states
// ---------------------------------------------------------------------------

/**
 * Canonical voice states. Every voice-enabled surface consumes these.
 * Lives in packages/shared-api/src/voice/state.ts at runtime; token colors
 * for each state are defined here for visual consistency.
 */
export type VoiceState =
  | "idle"
  | "listening"
  | "processing"
  | "confirming"
  | "success"
  | "error";

export const voiceStateTokens = {
  idle: {
    indicator: colors.neutral[400],
    label: "neutral.secondary",
    ring: null,
  },
  listening: {
    indicator: colors.alert[400],
    label: "alert.600",
    ring: colors.alert[200],
    pulse: true,
  },
  processing: {
    indicator: colors.brand[600],
    label: "brand.600",
    ring: null,
    dots: [colors.brand[400], colors.brand[600], colors.brand[200]],
  },
  confirming: {
    indicator: colors.alert[400],
    label: "alert.900",
    bannerBg: colors.alert[50],
    bannerBorder: colors.alert[400],
  },
  success: {
    indicator: colors.margin[600],
    label: "margin.600",
    ring: null,
    durationMs: 800, // Brief flash before dissolving to idle
  },
  error: {
    indicator: colors.fault[600],
    label: "fault.800",
    ring: colors.fault[200],
    recoverable: true, // Always pair with retry
  },
} as const;

// ---------------------------------------------------------------------------
// Motion
// ---------------------------------------------------------------------------

export const motion = {
  duration: {
    instant: 100,
    fast: 150,
    base: 200,
    slow: 300,
    voiceSuccess: 800, // Voice success state persistence
  },
  easing: {
    standard: "cubic-bezier(0.4, 0, 0.2, 1)",
    decelerate: "cubic-bezier(0, 0, 0.2, 1)",
    accelerate: "cubic-bezier(0.4, 0, 1, 1)",
  },
} as const;

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export const tokens = {
  colors,
  lightTheme,
  darkTheme,
  fonts,
  webFontSizes,
  webLineHeights,
  mobileFontSizes,
  mobileLineHeights,
  fontWeights,
  spacing,
  touchTargets,
  radii,
  voiceStateTokens,
  motion,
} as const;

export type Tokens = typeof tokens;
export type ColorRamp = keyof typeof colors;
export type ColorStop = keyof typeof colors.brand;
