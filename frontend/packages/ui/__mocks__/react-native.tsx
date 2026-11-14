/**
 * React Native test mock for packages/ui vitest
 *
 * Maps RN primitives to HTML equivalents so components render in jsdom.
 */

import React from "react";

// ── Shared prop filter ────────────────────────────────────────────────────────
// Remove RN-only props that DOM elements don't accept
function filterDOMProps(props: Record<string, unknown>) {
  const rnOnly = new Set([
    "style",
    "accessibilityRole",
    "accessibilityLabel",
    "accessibilityHint",
    "accessibilityState",
    "accessibilityViewIsModal",
    "accessibilityLiveRegion",
    "numberOfLines",
    "onLongPress",
    "delayLongPress",
    "pressRetentionOffset",
    "android_ripple",
    "unstable_pressDelay",
    "hitSlop",
  ]);
  return Object.fromEntries(
    Object.entries(props).filter(([k]) => !rnOnly.has(k)),
  );
}

// ── Component mocks ───────────────────────────────────────────────────────────

export function View({
  children,
  testID,
  ...rest
}: Record<string, unknown> & { children?: React.ReactNode; testID?: string }) {
  return (
    <div data-testid={testID} {...filterDOMProps(rest)}>
      {children}
    </div>
  );
}

export function Text({
  children,
  testID,
  ...rest
}: Record<string, unknown> & { children?: React.ReactNode; testID?: string }) {
  return (
    <span data-testid={testID} {...filterDOMProps(rest)}>
      {children}
    </span>
  );
}

export function Pressable({
  children,
  onPress,
  testID,
  disabled,
  ...rest
}: Record<string, unknown> & {
  children?: React.ReactNode;
  onPress?: () => void;
  testID?: string;
  disabled?: boolean;
}) {
  return (
    <button
      data-testid={testID}
      onClick={onPress}
      disabled={disabled}
      {...filterDOMProps(rest)}
    >
      {children}
    </button>
  );
}

export function ScrollView({
  children,
  testID,
  ...rest
}: Record<string, unknown> & { children?: React.ReactNode; testID?: string }) {
  return (
    <div data-testid={testID} {...filterDOMProps(rest)}>
      {children}
    </div>
  );
}

export function FlatList<T>({
  data,
  renderItem,
  keyExtractor,
  testID,
  ListEmptyComponent,
  ItemSeparatorComponent,
}: {
  data?: T[] | null;
  renderItem: (info: { item: T; index: number }) => React.ReactNode;
  keyExtractor?: (item: T, index: number) => string;
  testID?: string;
  ListEmptyComponent?: React.ReactNode;
  ItemSeparatorComponent?: React.ComponentType<unknown> | null;
  [key: string]: unknown;
}) {
  if (!data || data.length === 0) {
    return <div data-testid={testID}>{ListEmptyComponent ?? null}</div>;
  }
  return (
    <div data-testid={testID}>
      {data.map((item, index) => (
        <React.Fragment
          key={keyExtractor ? keyExtractor(item, index) : String(index)}
        >
          {renderItem({ item, index })}
          {ItemSeparatorComponent && index < data.length - 1 && (
            <ItemSeparatorComponent />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export function TextInput({
  testID,
  value,
  onChangeText,
  placeholder,
  ...rest
}: Record<string, unknown> & {
  testID?: string;
  value?: string;
  onChangeText?: (text: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      data-testid={testID}
      value={value}
      onChange={(e) => onChangeText?.(e.target.value)}
      placeholder={placeholder}
      {...filterDOMProps(rest)}
    />
  );
}

export function Modal({
  children,
  visible,
  testID,
}: {
  children?: React.ReactNode;
  visible?: boolean;
  testID?: string;
  [key: string]: unknown;
}) {
  if (!visible) return null;
  return (
    <div data-testid={testID} role="dialog" aria-modal="true">
      {children}
    </div>
  );
}

export function ActivityIndicator({
  testID,
  accessibilityLabel,
}: {
  testID?: string;
  accessibilityLabel?: string;
  [key: string]: unknown;
}) {
  return (
    <div
      data-testid={testID ?? "activity-indicator"}
      aria-label={accessibilityLabel ?? "Loading"}
      role="status"
    />
  );
}

// ── TouchableOpacity ─────────────────────────────────────────────────────────

export function TouchableOpacity({
  children,
  onPress,
  testID,
  disabled,
  ...rest
}: Record<string, unknown> & {
  children?: React.ReactNode;
  onPress?: () => void;
  testID?: string;
  disabled?: boolean;
  activeOpacity?: number;
}) {
  return (
    <button
      data-testid={testID}
      onClick={onPress}
      disabled={disabled}
      {...filterDOMProps(rest)}
    >
      {children}
    </button>
  );
}

// ── Utilities ─────────────────────────────────────────────────────────────────

export const StyleSheet = {
  create: <T extends Record<string, unknown>>(styles: T) => styles,
  flatten: (style: unknown) => style,
  hairlineWidth: 1,
};

export const Platform = {
  OS: "web" as const,
  Version: 0,
  select: <T extends Record<string, unknown>>(obj: T): T[keyof T] =>
    (obj.web ?? obj.default) as T[keyof T],
};

export const AccessibilityInfo = {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  announceForAccessibility: (_msg: string) => {
    // no-op in test environment
  },
  isScreenReaderEnabled: () => Promise.resolve(false),
  addEventListener: () => ({ remove: () => undefined }),
};

export const NativeModules = {};

export const Dimensions = {
  get: () => ({ width: 375, height: 812, scale: 2, fontScale: 1 }),
  addEventListener: () => ({ remove: () => undefined }),
};

// ── Linking ───────────────────────────────────────────────────────────────────
// Used by CalendarSyncStatusRow.tsx (FE-B8) to open web deep-link URLs.

export const Linking = {
  openURL: () => Promise.resolve(),
  canOpenURL: () => Promise.resolve(true),
  getInitialURL: () => Promise.resolve(null),
  addEventListener: () => ({ remove: () => undefined }),
};

// ── Default export ────────────────────────────────────────────────────────────

export default {
  View,
  Text,
  Pressable,
  TouchableOpacity,
  ScrollView,
  FlatList,
  TextInput,
  Modal,
  ActivityIndicator,
  StyleSheet,
  Platform,
  AccessibilityInfo,
  NativeModules,
  Dimensions,
  Linking,
};
