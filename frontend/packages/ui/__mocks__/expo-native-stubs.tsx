/**
 * Expo + react-native-svg stubs for packages/ui vitest
 *
 * MFA-WIRE-1 Part C: the mobile wizard imports expo-haptics, expo-clipboard,
 * and react-native-svg. These are native modules that don't exist in the
 * jsdom vitest environment. This stub provides minimal no-op implementations.
 */
import React from "react";
import { vi } from "vitest";

// ── react-native-svg — render Svg/Path as inert SVG elements ─────────────────

export function Svg({
  children,
  width,
  height,
  ...rest
}: Record<string, unknown> & { children?: React.ReactNode }) {
  return (
    <svg
      width={(width as number) ?? 24}
      height={(height as number) ?? 24}
      viewBox="0 0 24 24"
      data-testid="mock-svg"
      {...rest}
    >
      {children}
    </svg>
  );
}

export function Path() {
  return <path data-testid="mock-svg-path" />;
}

// Re-export common react-native-svg components as no-ops
export const Circle = () => null;
export const Rect = () => null;
export const Line = () => null;
export const G = ({ children }: { children?: React.ReactNode }) => (
  <>{children}</>
);
export const RNSvgText = () => null;
export const Defs = () => null;
export const LinearGradient = () => null;
export const Stop = () => null;

// Default export — some consumers use `import Svg from "react-native-svg"`
export default Svg;

// ── expo-haptics — no-op haptic feedback ──────────────────────────────────────

export const notificationAsync = vi.fn().mockResolvedValue(undefined);
export const impactAsync = vi.fn().mockResolvedValue(undefined);
export const selectionAsync = vi.fn().mockResolvedValue(undefined);
export const NotificationFeedbackType = {
  Success: "success",
  Warning: "warning",
  Error: "error",
};
export const ImpactFeedbackStyle = {
  Light: "light",
  Medium: "medium",
  Heavy: "heavy",
};

// ── expo-clipboard — no-op clipboard ──────────────────────────────────────────

export const setStringAsync = vi.fn().mockResolvedValue(true);
export const getStringAsync = vi.fn().mockResolvedValue("");
export const setString = vi.fn();
